import os
from pathlib import Path
from dotenv import load_dotenv

# Define base directory (project root: d:/edugenieai/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

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

# Retrieve Google Gemini API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def validate_config() -> None:
    """
    Validates that essential configurations and API keys are set.
    Raises ValueError if required configurations are missing.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY
    if not api_key or api_key == "YOUR_GEMINI_API_KEY" or not api_key.strip():
        raise ValueError(
            "GOOGLE_API_KEY is not set in the environment or .env file. "
            "Please obtain an API key from Google AI Studio and configure it."
        )


# Run validation on import to catch configuration errors early
# Removed validate_config() from automatic import execution to prevent startup crashes when the API key is not yet set.
# validate_config()

