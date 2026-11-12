
import os
import tempfile
import base64

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.voice_service import generate_speech
from backend.language_bridge import (
    translate_message,
    translate_detected_message
)
from backend.speech_service import transcribe_audio
from backend.audio_converter import convert_to_wav
from backend.agent import process_message, confirm_action


app = FastAPI(
    title="Voice Khata AI",
    description="Multilingual AI assistant for kirana shopkeepers",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class MessageRequest(BaseModel):
    message: str


class ConfirmationRequest(BaseModel):
    pending_action: dict
    confirmed: bool


class TranslationRequest(BaseModel):
    message: str
    source_language: str = "Auto-detect"
    target_language: str


class ConversationRequest(BaseModel):
    customer_message: str
    customer_language: str
    shopkeeper_language: str
    shopkeeper_reply: str


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_audio_suffix(content_type):
    """Get the correct temporary file extension."""

    if content_type.startswith("audio/webm"):
        return ".webm"

    if content_type == "audio/mpeg":
        return ".mp3"

    if content_type in ["audio/wav", "audio/x-wav"]:
        return ".wav"

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported audio format: {content_type}"
    )


async def save_and_convert_audio(audio):
    """Save uploaded audio and convert it into WAV."""

    suffix = get_audio_suffix(audio.content_type)

    temp_path = None
    converted_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:
            temp_file.write(await audio.read())
            temp_path = temp_file.name

        converted_path = temp_path + "_converted.wav"

        convert_to_wav(temp_path, converted_path)

        return temp_path, converted_path

    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        if converted_path and os.path.exists(converted_path):
            os.remove(converted_path)

        raise


def cleanup_audio_files(*paths):
    """Remove temporary audio files."""

    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                print("Could not remove temporary file:", path)


def encode_audio(audio_file_path):
    """Convert generated WAV audio into Base64."""

    with open(audio_file_path, "rb") as audio_file:
        return base64.b64encode(
            audio_file.read()
        ).decode("utf-8")


# --------------------------------------------------
# HOME AND HEALTH
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to Voice Khata AI!",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# --------------------------------------------------
# AI CHAT AND CONFIRMATION
# --------------------------------------------------

@app.post("/chat")
def chat(request: MessageRequest):
    try:
        return process_message(request.message)

    except Exception as e:
        print("CHAT ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to process your request."
        )


@app.post("/confirm")
def confirm(request: ConfirmationRequest):
    try:
        return confirm_action(
            request.pending_action,
            request.confirmed
        )

    except Exception as e:
        print("CONFIRMATION ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to process confirmation."
        )


# --------------------------------------------------
# TEXT TRANSLATION
# --------------------------------------------------

@app.post("/translate")
def translate(request: TranslationRequest):
    result = translate_message(
        request.message,
        request.source_language,
        request.target_language
    )

    if result["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=result["message"]
        )

    return result


# --------------------------------------------------
# TWO-WAY TEXT CONVERSATION
# --------------------------------------------------

@app.post("/conversation")
def conversation(request: ConversationRequest):

    customer_translation = translate_message(
        request.customer_message,
        request.customer_language,
        request.shopkeeper_language
    )

    if customer_translation["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail="Customer message translation failed."
        )

    shopkeeper_translation = translate_message(
        request.shopkeeper_reply,
        request.shopkeeper_language,
        request.customer_language
    )

    if shopkeeper_translation["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail="Shopkeeper reply translation failed."
        )

    return {
        "status": "success",
        "customer_to_shopkeeper": customer_translation["translated_message"],
        "shopkeeper_to_customer": shopkeeper_translation["translated_message"]
    }


# --------------------------------------------------
# SPEECH TO TEXT
# --------------------------------------------------

@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):

    temp_path = None
    converted_path = None

    try:
        temp_path, converted_path = await save_and_convert_audio(audio)

        result = transcribe_audio(converted_path)

        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )

        return result

    except HTTPException:
        raise

    except Exception as e:
        print("SPEECH TO TEXT ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Speech recognition failed."
        )

    finally:
        cleanup_audio_files(temp_path, converted_path)


# --------------------------------------------------
# CUSTOMER SPEAKS → SHOPKEEPER HEARS TRANSLATION
# --------------------------------------------------

@app.post("/translate-audio")
async def translate_audio(
    audio: UploadFile = File(...),
    target_language: str = Form("Kannada")
):

    temp_path = None
    converted_path = None

    try:
        temp_path, converted_path = await save_and_convert_audio(audio)

        # Detect customer language and transcribe speech
        speech_result = transcribe_audio(converted_path)

        if speech_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=speech_result["message"]
            )

        transcript = speech_result["transcript"]
        detected_language = speech_result["detected_language"]

        # Translate into the selected shopkeeper language
        translation_result = translate_detected_message(
            transcript,
            detected_language,
            target_language
        )

        if translation_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=translation_result["message"]
            )

        # Generate spoken translation
        tts_result = generate_speech(
            translation_result["translated_message"],
            target_language,
            "translated_response.wav"
        )

        if tts_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=tts_result["message"]
            )

        audio_base64 = encode_audio(tts_result["audio_file"])

        return {
            "status": "success",
            "original_transcript": transcript,
            "detected_language": detected_language,
            "target_language": target_language,
            "translated_message": translation_result["translated_message"],
            "audio_base64": audio_base64,
            "audio_format": "wav"
        }

    except HTTPException:
        raise

    except Exception as e:
        print("CUSTOMER AUDIO TRANSLATION ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Customer audio translation failed."
        )

    finally:
        cleanup_audio_files(temp_path, converted_path)


# --------------------------------------------------
# SHOPKEEPER REPLIES → CUSTOMER HEARS TRANSLATION
# --------------------------------------------------

@app.post("/reply-audio")
async def reply_audio(
    audio: UploadFile = File(...),
    customer_language: str = Form("te-IN")
):

    temp_path = None
    converted_path = None

    try:
        temp_path, converted_path = await save_and_convert_audio(audio)

        # Transcribe shopkeeper speech
        speech_result = transcribe_audio(converted_path)

        if speech_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=speech_result["message"]
            )

        transcript = speech_result["transcript"]
        shopkeeper_detected_language = speech_result["detected_language"]

        # Translate into customer's detected language
        translation_result = translate_detected_message(
            transcript,
            shopkeeper_detected_language,
            customer_language
        )

        if translation_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=translation_result["message"]
            )

        # Generate spoken reply for customer
        tts_result = generate_speech(
            translation_result["translated_message"],
            customer_language,
            "customer_reply.wav"
        )

        if tts_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=tts_result["message"]
            )

        audio_base64 = encode_audio(tts_result["audio_file"])

        return {
            "status": "success",
            "original_transcript": transcript,
            "shopkeeper_language": shopkeeper_detected_language,
            "customer_language": customer_language,
            "translated_message": translation_result["translated_message"],
            "audio_base64": audio_base64,
            "audio_format": "wav"
        }

    except HTTPException:
        raise

    except Exception as e:
        print("SHOPKEEPER REPLY TRANSLATION ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Shopkeeper reply translation failed."
        )

    finally:
        cleanup_audio_files(temp_path, converted_path)
