from dotenv import load_dotenv
load_dotenv()

from gnani.stt import GnaniSTTClient

client = GnaniSTTClient()


def transcribe_audio(file_path):
    try:
        result = client.transcribe(
            file_path,
            language_code="indic-auto",
            model="prisma-v3.0"
        )

        return {
            "status": "success",
            "transcript": result["transcript"],
            "detected_language": result.get("detected_language_code")
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
