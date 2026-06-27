import logging
from pathlib import Path
from typing import Optional
from src.utils.document_processors import create_documents_from_pdf, extract_text_from_pdf
from src.rag.vector_store import add_documents, similarity_search
from src.rag.llm_service import LLMService

# Set up logger
logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    Orchestrates the RAG (Retrieval-Augmented Generation) pipeline:
    indexing documents, retrieving context, and generating tutoring answers/quizzes/notes.
    """
    def __init__(self):
        """
        Initializes the pipeline with the LLM Service.
        """
        try:
            self.llm_service = LLMService()
            self.current_pdf_path: Optional[Path] = None
            logger.info("RAGPipeline initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RAGPipeline: {e}", exc_info=True)
            raise RuntimeError(f"Pipeline initialization failed: {str(e)}")

    def index_pdf(self, pdf_path: str, user_id: int) -> None:
        """
        Processes a PDF, splits it, stores its embeddings in ChromaDB user collection, and sets it active.

        Args:
            pdf_path (str): File path to the PDF document.
            user_id (int): ID of the user.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

        try:
            logger.info(f"Indexing PDF document: {path.name} for user {user_id}")
            
            # 1. Extract and split PDF text into LangChain Documents
            documents = create_documents_from_pdf(path)
            
            if not documents:
                raise ValueError(f"No readable text could be extracted from {path.name}.")
                
            # 2. Store document embeddings in user ChromaDB collection
            add_documents(documents, user_id)
            
            # 3. Track current document path in session
            self.current_pdf_path = path
            logger.info(f"Successfully indexed and set {path.name} as the active document for user {user_id}.")
        except Exception as e:
            logger.error(f"Failed to index PDF {path.name} for user {user_id}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to index document: {str(e)}")

    def ask(self, question: str, user_id: int, k: int = 4) -> str:
        """
        Answers a user's question by performing retrieval-augmented generation.

        Args:
            question (str): User query.
            user_id (int): ID of the user.
            k (int): Number of document chunks to retrieve as context.

        Returns:
            str: Tutoring answer in Markdown.
        """
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        try:
            logger.info(f"RAG query received from user {user_id}: '{question}'")
            
            # 1. Retrieve matching chunks from the user vector database collection
            matching_docs = similarity_search(question, user_id, k=k)
            
            # 2. Format context by joining chunk contents
            if not matching_docs:
                logger.warning(f"No matching document chunks found in vector store for user {user_id}.")
                context = "No relevant context found in the uploaded document database."
            else:
                context = "\n\n---\n\n".join([doc.page_content for doc in matching_docs])
            
            # 3. Ask LLM to generate answer using the retrieved context
            answer = self.llm_service.generate_answer(question, context)
            return answer
        except Exception as e:
            logger.error(f"Error executing ask pipeline for user {user_id}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to retrieve and answer: {str(e)}")

    def generate_notes(self) -> str:
        """
        Generates comprehensive study notes from the currently active PDF.

        Returns:
            str: Study notes in Markdown.
        """
        if not self.current_pdf_path:
            raise ValueError("No active PDF has been indexed. Please index a PDF first.")

        try:
            logger.info(f"Generating study notes for active PDF: {self.current_pdf_path.name}")
            
            # Extract full text of the active PDF to ensure comprehensive summarization
            full_text = extract_text_from_pdf(self.current_pdf_path)
            
            if not full_text:
                raise ValueError("Could not read content from the active PDF.")
                
            # Send full text context to LLM for notes generation
            return self.llm_service.generate_notes(full_text)
        except Exception as e:
            logger.error(f"Failed to generate notes: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate study notes: {str(e)}")

    def generate_quiz(self, num_questions: int = 5) -> str:
        """
        Generates a multiple-choice quiz from the currently active PDF.

        Args:
            num_questions (int): Number of questions to generate.

        Returns:
            str: Multiple choice quiz in Markdown.
        """
        if not self.current_pdf_path:
            raise ValueError("No active PDF has been indexed. Please index a PDF first.")

        try:
            logger.info(f"Generating quiz from active PDF: {self.current_pdf_path.name}")
            
            # Extract full text of the active PDF
            full_text = extract_text_from_pdf(self.current_pdf_path)
            
            if not full_text:
                raise ValueError("Could not read content from the active PDF.")

            # Send text to LLM to generate the quiz
            return self.llm_service.generate_quiz(full_text, num_questions)
        except Exception as e:
            logger.error(f"Failed to generate quiz: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate quiz: {str(e)}")

    def generate_quiz_structured(self, num_questions: int = 5):
        """
        Generates a structured multiple-choice quiz from the currently active PDF.

        Args:
            num_questions (int): Number of questions to generate.

        Returns:
            QuizSchema: Quiz object containing structured questions, choices, correct answers, and explanations.
        """
        if not self.current_pdf_path:
            raise ValueError("No active PDF has been indexed. Please index a PDF first.")

        try:
            logger.info(f"Generating structured quiz from active PDF: {self.current_pdf_path.name}")
            
            # Extract full text of the active PDF
            full_text = extract_text_from_pdf(self.current_pdf_path)
            
            if not full_text:
                raise ValueError("Could not read content from the active PDF.")

            # Send text to LLM to generate the structured quiz
            return self.llm_service.generate_quiz_structured(full_text, num_questions)
        except Exception as e:
            logger.error(f"Failed to generate structured quiz: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate structured quiz: {str(e)}")

    def generate_and_save_flashcards(self, user_id: int, document_name: str, num_cards: int = 10) -> int:
        """
        Generates structured flashcards from active document text, stores them in SQLite db,
        and returns count of cards generated.
        """
        if not self.current_pdf_path:
            raise ValueError("No active PDF has been indexed. Please index a PDF first.")

        try:
            logger.info(f"Generating flashcards for active PDF: {self.current_pdf_path.name}")
            
            # Extract text of the active PDF
            full_text = extract_text_from_pdf(self.current_pdf_path)
            
            if not full_text:
                raise ValueError("Could not read content from the active PDF.")

            # Generate using LLM Service
            structured_data = self.llm_service.generate_flashcards_structured(full_text, num_cards)
            
            if not structured_data or not structured_data.flashcards:
                raise ValueError("LLM failed to return structured flashcards.")

            # Clear existing flashcards for this user and document to prevent accumulation on regeneration
            from src.database.db_manager import delete_all_flashcards, add_flashcard
            delete_all_flashcards(user_id, document_name)
            
            count = 0
            for card in structured_data.flashcards:
                if add_flashcard(user_id, document_name, card.question, card.answer):
                    count += 1
            
            logger.info(f"Successfully generated and saved {count} flashcards for '{document_name}'")
            return count
        except Exception as e:
            logger.error(f"Failed to generate and save flashcards: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate and save flashcards: {str(e)}")

