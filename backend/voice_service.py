from dotenv import load_dotenv
load_dotenv()

from gnani.tts import GnaniTTSClient

client = GnaniTTSClient()

LANGUAGE_CODES = {
    "english": "en-IN",
    "hindi": "hi-IN",
    "bengali": "bn-IN",
    "marathi": "mr-IN",
    "gujarati": "gu-IN",
    "punjabi": "pa-IN",
    "kannada": "kn-IN",
    "telugu": "te-IN",
    "tamil": "ta-IN",
    "malayalam": "ml-IN"
}


def generate_speech(text, language, output_file="response.wav"):
    try:
        language_code = LANGUAGE_CODES.get(
            language.lower(),
            language
        )

        audio = client.synthesize(
            text=text,
            voice="Chetana",
            model="timbre-v3.0",
            language=language_code,
            output_file=output_file
        )

        return {
            "status": "success",
            "audio_file": output_file,
            "language": language_code
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
