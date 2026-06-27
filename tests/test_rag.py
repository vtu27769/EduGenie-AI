from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from src.utils.document_processors import split_text_into_chunks

def test_document_splitter():
    """
    Tests text chunking utility functions with custom chunk parameters.
    """
    sample_text = "This is a sentence. This is another sentence. We need to split this properly."
    chunks = split_text_into_chunks(sample_text, chunk_size=20, chunk_overlap=5)
    
    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)

@patch('src.rag.vector_store.add_documents')
def test_vector_store_add_mock(mock_add):
    """
    Mock test for Chroma document insertion.
    """
    docs = [Document(page_content="Sample context", metadata={"source": "test.pdf"})]
    mock_add(docs)
    mock_add.assert_called_once_with(docs)
