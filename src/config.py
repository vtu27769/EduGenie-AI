import os
from pathlib import Path
from dotenv import load_dotenv

# Define base directory (project root: d:/edugenieai/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
print("BASE_DIR =", BASE_DIR)
print("ENV_PATH =", ENV_PATH)
print("AZURE_OPENAI_ENDPOINT =", bool(os.getenv("AZURE_OPENAI_ENDPOINT")))
print("AZURE_OPENAI_API_KEY =", bool(os.getenv("AZURE_OPENAI_API_KEY")))
print("AZURE_OPENAI_DEPLOYMENT =", bool(os.getenv("AZURE_OPENAI_DEPLOYMENT")))

# Define directories for project data
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = DATA_DIR / "chroma"
SQLITE_DB_PATH = DATA_DIR / "edugenie.db"
UPLOAD_DIR = BASE_DIR / "uploads"

# Create directories if they do not exist
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    raise IOError(f"Failed to create necessary project directories: {e}")

# Retrieve Azure OpenAI Credentials
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

def validate_config():
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    if not endpoint or not api_key or not deployment or not api_version:
        raise ValueError(
            "Azure OpenAI configuration is incomplete."
        )


# Run validation on import to catch configuration errors early
# Removed validate_config() from automatic import execution to prevent startup crashes when the API key is not yet set.
# validate_config()

