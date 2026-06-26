import logging
from typing import List, Optional, Dict
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from src.config import CHROMA_DB_DIR

# Set up logger
logger = logging.getLogger(__name__)

# Global cache of vector stores mapped by user_id
_vector_stores: Dict[int, Chroma] = {}
_embeddings: Optional[HuggingFaceEmbeddings] = None

def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Initializes and caches the HuggingFace embeddings model.
    """
    global _embeddings
    if _embeddings is None:
        try:
            logger.info("Initializing HuggingFaceEmbeddings with all-MiniLM-L6-v2...")
            _embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},  # Default to CPU for portability
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("HuggingFaceEmbeddings initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFaceEmbeddings: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load embedding model: {str(e)}")
    return _embeddings

def initialize_vector_store(user_id: int) -> Chroma:
    """
    Initializes or retrieves the persistent ChromaDB vector store for a specific user.

    Returns:
        Chroma: The initialized LangChain Chroma vector store wrapper.
    """
    global _vector_stores
    if user_id not in _vector_stores:
        try:
            logger.info(f"Initializing ChromaDB at: {CHROMA_DB_DIR} for user {user_id}")
            embeddings = get_embeddings()
            _vector_stores[user_id] = Chroma(
                collection_name=f"user_{user_id}_collection",
                embedding_function=embeddings,
                persist_directory=str(CHROMA_DB_DIR)
            )
            logger.info(f"ChromaDB vector store for user {user_id} initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB for user {user_id}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize vector store: {str(e)}")
    return _vector_stores[user_id]

def add_documents(documents: List[Document], user_id: int) -> None:
    """
    Adds a list of LangChain Document objects to the ChromaDB vector store of a specific user.

    Args:
        documents (List[Document]): The documents/chunks to add.
        user_id (int): ID of the user.
    
    Raises:
        ValueError: If documents list is empty.
        RuntimeError: If ChromaDB fails to add the documents.
    """
    if not documents:
        logger.warning("Empty list of documents provided to add_documents.")
        return

    try:
        vector_store = initialize_vector_store(user_id)
        logger.info(f"Adding {len(documents)} documents to ChromaDB for user {user_id}...")
        
        # Batch addition/persist is handled automatically in langchain-chroma
        vector_store.add_documents(documents)
        logger.info(f"Successfully added documents to ChromaDB for user {user_id}.")
    except Exception as e:
        logger.error(f"Failed to add documents to ChromaDB for user {user_id}: {e}", exc_info=True)
        raise RuntimeError(f"Failed to add documents to vector database: {str(e)}")

def similarity_search(query: str, user_id: int, k: int = 4) -> List[Document]:
    """
    Performs a similarity search on ChromaDB for a given text query inside a specific user's store.

    Args:
        query (str): The search query.
        user_id (int): ID of the user.
        k (int): The number of relevant documents to retrieve.

    Returns:
        List[Document]: List of matching LangChain Document objects.
    """
    if not query.strip():
        logger.warning("Empty query provided to similarity_search.")
        return []

    try:
        vector_store = initialize_vector_store(user_id)
        logger.info(f"Performing similarity search for query: '{query}' (k={k}) for user {user_id}")
        results = vector_store.similarity_search(query, k=k)
        logger.info(f"Retrieved {len(results)} matching documents for user {user_id}.")
        return results
    except Exception as e:
        logger.error(f"Similarity search failed for user {user_id} and query '{query}': {e}", exc_info=True)
        raise RuntimeError(f"Failed to query vector database: {str(e)}")
