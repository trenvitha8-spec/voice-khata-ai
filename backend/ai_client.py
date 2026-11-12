import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.6-flash"


def ask_gemini(message):
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=message
    )

    return response.text


if __name__ == "__main__":
    answer = ask_gemini(
        "You are Voice Khata AI, a helpful assistant for kirana shopkeepers. "
        "Introduce yourself in two simple sentences."
    )
    print("Gemini response:")
    print(answer)
