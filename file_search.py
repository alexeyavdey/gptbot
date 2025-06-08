from typing import Dict, Optional
from PyPDF2 import PdfReader

from .client import client
from .logger import create_logger
from .constants import GPT4_MODEL

logger = create_logger(__name__)

# Store user vector store IDs: user_id -> vector_store_id
user_vector_stores: Dict[int, str] = {}


async def process_pdf(user_id: int, file_path: str) -> str:
    logger.info(f"process_pdf:start:{user_id}:{file_path}")
    
    try:
        # Delete previous vector store if exists
        await clear_store(user_id)
        
        # Create new vector store for this user
        vector_store = await client.vector_stores.create(
            name=f"user_{user_id}_pdf_store"
        )
        vector_store_id = vector_store.id
        user_vector_stores[user_id] = vector_store_id
        logger.info(f"process_pdf:created_vector_store:{user_id}:{vector_store_id}")
        
        # Upload PDF file to vector store
        with open(file_path, 'rb') as file:
            file_response = await client.files.create(
                file=file,
                purpose="assistants"
            )
            
        await client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_response.id
        )
        logger.info(f"process_pdf:uploaded_file:{user_id}:{file_response.id}")
        
        # Generate summary using traditional method
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        summary_prompt = f"Summarize the following text:\n{text}"[:8000]
        
        response = await client.chat.completions.create(
            model=GPT4_MODEL,
            messages=[{"role": "user", "content": summary_prompt}]
        )
        summary = response.choices[0].message.content.strip()
        logger.info(f"process_pdf:summary_done:{user_id}")
        return summary
        
    except Exception as e:
        logger.error(f"process_pdf:error:{user_id}:{e}")
        return f"Error processing PDF: {str(e)}"


async def search_context(user_id: int, query: str) -> str:
    vector_store_id = user_vector_stores.get(user_id)
    if not vector_store_id:
        logger.info(f"search_context:no_vector_store:{user_id}")
        return ""
    
    try:
        # Use OpenAI's file search with vector store
        response = await client.chat.completions.create(
            model=GPT4_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Use the provided documents to answer questions. If you can't find relevant information in the documents, say so."
                },
                {
                    "role": "user", 
                    "content": f"Based on the uploaded documents, provide relevant context for this query: {query}"
                }
            ],
            tools=[
                {
                    "type": "file_search",
                    "file_search": {
                        "vector_store_ids": [vector_store_id]
                    }
                }
            ]
        )
        
        # Extract the response content
        if response.choices[0].message.content:
            context = response.choices[0].message.content.strip()
            logger.info(f"search_context:found:{user_id}")
            return context
        else:
            logger.info(f"search_context:no_content:{user_id}")
            return ""
            
    except Exception as e:
        logger.error(f"search_context:error:{user_id}:{e}")
        return ""


async def clear_store(user_id: int):
    vector_store_id = user_vector_stores.get(user_id)
    if vector_store_id:
        try:
            await client.vector_stores.delete(vector_store_id)
            user_vector_stores.pop(user_id, None)
            logger.info(f"clear_store:deleted:{user_id}:{vector_store_id}")
        except Exception as e:
            logger.error(f"clear_store:error:{user_id}:{e}")
            # Remove from local dict anyway in case of API error
            user_vector_stores.pop(user_id, None)
