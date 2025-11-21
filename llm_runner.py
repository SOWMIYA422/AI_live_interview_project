# llm_runner.py
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMRunner:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found")

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
            logger.info(f"✅ Gemini model {GEMINI_MODEL} initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            raise

    def generate_text(self, prompt, max_retries=3):
        for attempt in range(max_retries):
            try:
                # SIMPLE API CALL - Just like your working code
                response = self.model.generate_content(prompt)

                # DIRECT TEXT ACCESS - Same as your working resp.text
                if hasattr(response, "text") and response.text:
                    return response.text.strip()
                else:
                    return "Please continue with your answer."

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return "Please continue with your answer."

    def ask(self, prompt):
        return self.generate_text(prompt)
