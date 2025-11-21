import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Vosk config - using your existing path
VOSK_MODEL_PATH = (
    r"C:\Users\lenovo\Downloads\vosk-model-small-en-us-0.15\vosk-model-small-en-us-0.15"
)
SAMPLE_RATE = 16000

# Gemini API config - using your existing API key
GEMINI_API_KEY = "AIzaSyCN8n0bEesKmM0OxJBIq4aE1nYEsZPXYj8"
GEMINI_MODEL = "gemini-2.5-flash"

# Interview config
INTERVIEW_CONFIG = {
    "max_questions": 10,
    "time_per_question": 180,
}

# System paths
OUTPUT_DIR = "interview_sessions"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Job role specific prompts
JOB_ROLE_PROMPTS = {
    "software_engineer": {
        "opening": "Welcome! I'm your AI interviewer for the Software Engineer position. Let's start with a brief introduction. Could you please introduce yourself and tell me about your background in software development?",
        "context": "Software Engineer interview focusing on technical skills and experience.",
    },
    "data_scientist": {
        "opening": "Hello! I'm your AI interviewer for the Data Scientist role. To begin, could you please introduce yourself and share your experience with data analysis?",
        "context": "Data Scientist interview focusing on analytical skills and experience.",
    },
    "product_manager": {
        "opening": "Welcome! I'm your AI interviewer for the Product Manager position. Let's start with you introducing yourself and your product experience.",
        "context": "Product Manager interview focusing on product strategy and experience.",
    },
    "default": {
        "opening": "Welcome! I'm your AI interviewer. Please introduce yourself and tell me about your professional background.",
        "context": "Professional job interview.",
    },
}
