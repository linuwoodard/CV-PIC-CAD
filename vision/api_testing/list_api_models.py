import os
from google.genai import Client
from dotenv import load_dotenv


def list_models():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ Error: Could not find 'GEMINI_API_KEY'.")
        return

    print("🔍 Searching for available models...")
    try:
        with Client(api_key=api_key) as client:
            # List available models
            models = client.models.list()
            for model in models:
                # Check if model supports content generation
                if hasattr(model, 'supported_generation_methods') and 'generateContent' in model.supported_generation_methods:
                    print(f" - Found: {model.name}")
                elif hasattr(model, 'name'):
                    # If we can't check methods, just list by name
                    print(f" - Found: {model.name}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")

if __name__ == "__main__":
    list_models()