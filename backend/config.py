import os
from dotenv import load_dotenv

# Load the variables from the .env file
load_dotenv()

# Read the keys from the environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")