import os
from dotenv import load_dotenv

def init_config():
    """Load ecosystem environment variables."""
    load_dotenv()

def get_env(key: str, default: str = None) -> str:
    """Read env with fallback."""
    return os.getenv(key, default)
