import logging
import os
from typing import List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Set up logger
logger = logging.getLogger(__name__)

# Pydantic schemas for structured quiz generation
class QuizQuestionSchema(BaseModel):
    question: str = Field(description="The question text asking about the context.")
    options: List[str] = Field(description="Exactly 4 multiple-choice options. E.g. ['Choice A', 'Choice B', 'Choice C', 'Choice D']")
    correct_answer: str = Field(description="The letter of the correct choice. Must be exactly 'A', 'B', 'C', or 'D'.")
    explanation: str = Field(description="A brief explanation of why this option is correct based on the context.")

class QuizSchema(BaseModel):
    questions: List[QuizQuestionSchema]

class LLMService:
    """
    Service layer for communicating with Google Gemini using LangChain.
    """
    def __init__(self, temperature: float = 0.2):
        """
        Initializes the service with temperature setting. LLM client is generated lazily.
        """
        self.temperature = temperature
        logger.info("LLMService initialized with lazy client creation.")

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        """
        Retrieves the LLM client initialized dynamically with the latest API key in environment.
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY" or not api_key.strip():
            logger.error("Attempted to initialize LLM with missing or placeholder API Key.")
            raise ValueError(
                "Google Gemini API Key is missing or invalid. "
                "Please configure your key in the Settings page to activate AI operations."
            )
        
        logger.info("Initializing ChatGoogleGenerativeAI client dynamically...")
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=self.temperature,
            max_retries=2
        )

    def generate_answer(self, question: str, context: str) -> str:
        """
        Generates an answer to a question based on the provided document context.

        Args:
            question (str): The user's question.
            context (str): The document context retrieved from vector store.

        Returns:
            str: Markdown formatted answer.
        """
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        try:
            logger.info("Generating answer using Gemini...")
            llm = self._get_llm()
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are EduGenie AI, an expert, encouraging academic tutor. "
                    "Answer the question based strictly on the provided context. If the answer "
                    "cannot be found in the context, clearly explain that it is not in the text, "
                    "and then provide a helpful response using your general knowledge, indicating the difference. "
                    "Format your answer using clean, structure-rich Markdown with bold highlights, tables, or bullet points where appropriate."
                )),
                ("user", "Context:\n{context}\n\nQuestion: {question}")
            ])
            
            chain = prompt | llm
            response = chain.invoke({"context": context, "question": question})
            return response.content
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate answer: {str(e)}")

    def generate_notes(self, context: str) -> str:
        """
        Generates comprehensive study notes from the provided text context.

        Args:
            context (str): The document context.

        Returns:
            str: Markdown formatted study notes.
        """
        if not context.strip():
            raise ValueError("Context cannot be empty for notes generation.")

        try:
            logger.info("Generating study notes using Gemini...")
            llm = self._get_llm()
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are EduGenie AI, a top-tier academic summary designer. "
                    "Your task is to take the provided context and transform it into high-quality, comprehensive study notes. "
                    "Organize the notes into logical headers, highlight key terms, define complex formulas or terms, "
                    "and add a short summary or takeaway section. "
                    "Format the entire output in clean, elegant Markdown."
                )),
                ("user", "Generate study notes for the following context:\n\n{context}")
            ])
            
            chain = prompt | llm
            response = chain.invoke({"context": context})
            return response.content
        except Exception as e:
            logger.error(f"Error generating notes: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate study notes: {str(e)}")

    def generate_quiz(self, context: str, num_questions: int = 5) -> str:
        """
        Generates a multiple-choice quiz based on the provided text context (legacy markdown fallback).

        Args:
            context (str): The document context.
            num_questions (int): Number of questions to generate.

        Returns:
            str: Markdown formatted quiz.
        """
        if not context.strip():
            raise ValueError("Context cannot be empty for quiz generation.")

        try:
            logger.info(f"Generating {num_questions} quiz questions in Markdown fallback...")
            llm = self._get_llm()
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an expert assessment generator. Create a multiple-choice quiz based on the provided context. "
                    "Provide exactly {num_questions} distinct questions. "
                    "For each question, follow this structure:\n"
                    "1. Question text\n"
                    "2. 4 choices labeled A, B, C, D\n"
                    "3. Correct option (clearly specified, e.g., 'Correct Answer: B')\n"
                    "4. A brief, educational explanation of why it is correct.\n\n"
                    "Ensure the output uses clean Markdown headers for each question."
                )),
                ("user", "Generate a quiz from this context:\n\n{context}")
            ])
            
            chain = prompt | llm
            response = chain.invoke({"context": context, "num_questions": num_questions})
            return response.content
        except Exception as e:
            logger.error(f"Error generating quiz fallback: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate quiz: {str(e)}")

    def generate_quiz_structured(self, context: str, num_questions: int = 5) -> QuizSchema:
        """
        Generates a structured Pydantic QuizSchema object from the provided context.
        """
        if not context.strip():
            raise ValueError("Context cannot be empty for quiz generation.")

        try:
            logger.info(f"Generating {num_questions} structured quiz questions using Gemini structured output...")
            llm = self._get_llm()
            
            # Request structured output using langchain interface
            structured_llm = llm.with_structured_output(QuizSchema)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an expert test creator. "
                    "Create a multiple-choice quiz based on the provided context. "
                    "Generate exactly {num_questions} distinct questions. "
                    "Make sure the options list for each question has exactly 4 options. "
                    "Provide the correct_answer as exactly 'A', 'B', 'C', or 'D'."
                )),
                ("user", "Generate a quiz from this context:\n\n{context}")
            ])
            
            chain = prompt | structured_llm
            response = chain.invoke({"context": context, "num_questions": num_questions})
            return response
        except Exception as e:
            logger.error(f"Error generating structured quiz: {e}", exc_info=True)
            # If structured output fails, log error and raise
            raise RuntimeError(f"Failed to generate structured quiz: {str(e)}")
