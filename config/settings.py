import json
from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    def __init__(self):
        # Prefer explicit WAHA_URL, fall back to WAHA_URL (helpful when services run on different hosts)
        # Default to the compose service name used in Docker networks.
        self.WAHA_URL = os.getenv('WAHA_URL') or 'http://waha:3000'
        self.GROQ_API_KEY = os.getenv('GROQ_API_KEY')
        self.HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
        self.GROQ_AI_MODEL = os.getenv('GROQ_AI_MODEL')
        self.COHERE_API_KEY = os.getenv('COHERE_API_KEY')
        self.CHROMA_API_KEY = os.getenv('CHROMA_API_KEY')
        self.CHROMA_TENANT_ID = os.getenv('CHROMA_TENANT_ID')
        self.CHROMA_DATABASE = os.getenv('CHROMA_DATABASE')
        self.WAHA_API_KEY = os.getenv('WAHA_API_KEY')
        self.ALLOW_ORIGINS = json.loads(os.getenv('ALLOW_ORIGINS', "[]").strip())
        self.GROQ_AI_GUARDRAILS_MODEL = os.getenv('GROQ_AI_GUARDRAILS_MODEL')