from dotenv import load_dotenv
load_dotenv()

from gnani.stt import GnaniSTTClient

client = GnaniSTTClient()

result = client.transcribe(
    "telugu_test.mp3",
    language_code="indic-auto",
    model="prisma-v3.0"
)

print("Transcript:", result["transcript"])
print("Detected language:", result.get("detected_language_code"))

