import logging
from pathlib import Path
from typing import List, Union
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Set up logger
logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: Union[str, Path]) -> str:
    """
    Extracts all text content from a PDF file.

    Args:
        file_path (str or Path): Path to the PDF file.

    Returns:
        str: Extracted text content.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid PDF or is encrypted.
        RuntimeError: For other processing failures.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {path}")
        raise FileNotFoundError(f"The file {path.name} does not exist.")

    if path.suffix.lower() != ".pdf":
        logger.error(f"Invalid file type: {path.suffix}")
        raise ValueError(f"File {path.name} is not a PDF file.")

    try:
        reader = PdfReader(path)
        
        # Check encryption
        if reader.is_encrypted:
            logger.error(f"Encrypted PDF file: {path}")
            raise ValueError(f"The PDF file {path.name} is encrypted and cannot be processed.")

        text_parts = []
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
            else:
                logger.warning(f"Could not extract text from page {page_num + 1} of {path.name}")
        
        full_text = "\n".join(text_parts).strip()
        if not full_text:
            logger.warning(f"No text extracted from PDF: {path.name}")
            
        return full_text

    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {path.name}: {e}", exc_info=True)
        raise RuntimeError(f"Failed to process PDF file: {str(e)}")

def split_text_into_chunks(
    text: str, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[str]:
    """
    Splits text content into clean string chunks.

    Args:
        text (str): The raw text to split.
        chunk_size (int): Max size of each chunk.
        chunk_overlap (int): Overlap size between adjacent chunks.

    Returns:
        List[str]: List of text chunks.
    """
    if not text:
        return []

    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        return splitter.split_text(text)
    except Exception as e:
        logger.error(f"Error splitting text: {e}", exc_info=True)
        raise RuntimeError(f"Failed to split text into chunks: {str(e)}")

def create_documents_from_pdf(
    file_path: Union[str, Path], 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[Document]:
    """
    Extracts text from a PDF file and splits it into LangChain Document objects 
    with metadata for vector storage.

    Args:
        file_path (str or Path): Path to the PDF file.
        chunk_size (int): Max size of each chunk.
        chunk_overlap (int): Overlap size between adjacent chunks.

    Returns:
        List[Document]: List of LangChain Document objects ready for embedding.
    """
    path = Path(file_path)
    text = extract_text_from_pdf(path)
    
    if not text:
        return []

    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Create initial Document object to preserve metadata
        doc = Document(
            page_content=text,
            metadata={"source": path.name, "file_path": str(path.absolute())}
        )
        
        return splitter.split_documents([doc])
    except Exception as e:
        logger.error(f"Error creating documents from PDF {path.name}: {e}", exc_info=True)
        raise RuntimeError(f"Failed to split document into chunks: {str(e)}")
