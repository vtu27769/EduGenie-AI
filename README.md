# EduGenie AI 🧞

EduGenie AI is a production-ready, AI-powered personal tutor and study companion application built using Python, Streamlit, LangChain, ChromaDB, and Google Gemini models.

## Features

1. **📖 Study Assistant**: Upload textbooks/lecture PDFs, index them into a high-performance vector database, ask complex context-driven questions, and generate comprehensive formatted study notes.
2. **📝 Quiz Generator**: Automatically generate custom multiple-choice quizzes (MCQs) directly from uploaded documents, complete with answer keys and educational explanations.
3. **⚙️ Settings & System Metrics**: Manage your Gemini credentials, test API latency/connectivity, and review database storage directories.

## Tech Stack

* **UI Layer**: Streamlit (with premium styling custom design tokens)
* **LLM Engine**: Google Gemini 2.5 Flash via LangChain (`langchain-google-genai`)
* **Vector Store**: ChromaDB (`langchain-chroma`)
* **Embeddings Model**: HuggingFace Sentence Transformers (`all-MiniLM-L6-v2`)
* **Document Processing**: `pypdf` with Recursive Text Splitting
* **Relational Storage**: SQLite

## Getting Started

### 1. Clone the Project & Set Up Environment

Make sure you have Python 3.10+ installed.

```bash
# Initialize virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials

Create a `.env` file from the template:
```bash
cp .env.example .env
```
And add your Google Gemini API Key:
```text
GOOGLE_API_KEY=AIzaSy...
```

### 3. Run the Application

```bash
streamlit run app.py
```
This will start the local development server. You can view the application in your browser at `http://localhost:8501`.
