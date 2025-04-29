from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    def __init__(self):
        self.API_URL = os.getenv('API_URL')
        self.GROQ_API_KEY = os.getenv('GROQ_API_KEY')