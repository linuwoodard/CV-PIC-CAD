import os
import google.generativeai as genai
from dotenv import load_dotenv


def test_gemini_connection():
    # 1. Load the secret from .env
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    # Sanity Check: Did it actually find the file?
    if not api_key:
        print("❌ Error: Could not find 'GEMINI_API_KEY'.")
        print("   - Check that you have a .env file in this folder.")
        print("   - Check that the variable name matches exactly.")
        return

    print(f"✅ Found API Key: {api_key[:5]}...{api_key[-4:]}")

    # 2. Configure the API
    try:
        genai.configure(api_key=api_key)
        
        # 3. Send a simple 'Ping' (Text only, no image needed yet)
        print("📡 Connecting to Gemini API...")
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Reply with exactly the word 'Pong'.")
        
        # 4. Check results
        if response.text.strip() == "Pong":
            print("✅ SUCCESS: API Connection established!")
            print(f"   Response received: {response.text}")
        else:
            print(f"⚠️  Connected, but unexpected response: {response.text}")

    except Exception as e:
        print(f"\n❌ CONNECTION FAILED")
        print(f"   Error details: {e}")

if __name__ == "__main__":
    test_gemini_connection()