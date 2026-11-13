
import os
import tempfile
import base64
import sqlite3

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.voice_service import generate_speech
from backend.language_bridge import (
    translate_message,
    translate_detected_message
)
from backend.speech_service import transcribe_audio
from backend.audio_converter import convert_to_wav
from backend.agent import process_message, confirm_action

from backend.database import initialize_database
from backend.ledger import (
    add_customer,
    get_all_customers,
    get_customer_balance,
    get_transaction_history,
    record_transaction,
    add_product,
    get_all_products,
    update_stock,
    record_sale,
    record_expense,
    get_all_expenses,
    get_daily_business_summary,
)


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
# DATABASE INITIALIZATION
# --------------------------------------------------

@app.on_event("startup")
def startup_event():
    initialize_database()


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


class CustomerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class KhataTransactionRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    transaction_type: str
    amount: float = Field(gt=0)
    description: str = ""


class ProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0)
    quantity: int = Field(ge=0)


class StockUpdateRequest(BaseModel):
    product_name: str = Field(min_length=1)
    quantity_change: int


class SaleRequest(BaseModel):
    product_name: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    payment_method: str = "CASH"


class ExpenseRequest(BaseModel):
    category: str = Field(min_length=1)
    amount: float = Field(gt=0)
    description: str = ""


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_audio_suffix(content_type):
    """Get the correct temporary file extension."""

    if content_type and content_type.startswith("audio/webm"):
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
        cleanup_audio_files(temp_path, converted_path)
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


def serialize_rows(rows):
    """Convert SQLite rows into JSON-compatible dictionaries."""

    return [dict(row) for row in rows]


def handle_database_error(error):
    """Convert expected database errors into HTTP responses."""

    if isinstance(error, (ValueError, sqlite3.IntegrityError)):
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    print("DATABASE ERROR:", repr(error))

    raise HTTPException(
        status_code=500,
        detail="A database operation failed."
    )


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
    try:
        result = translate_message(
            request.message,
            request.target_language,
            request.source_language
        )

        return {
            "status": "success",
            "original_message": request.message,
            "translated_message": result,
            "source_language": request.source_language,
            "target_language": request.target_language
        }

    except Exception as e:
        print("TEXT TRANSLATION ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# --------------------------------------------------
# TWO-WAY TEXT CONVERSATION
# --------------------------------------------------


@app.post("/conversation")
def conversation(request: ConversationRequest):
    try:
        # Customer message → Shopkeeper language
        customer_translation = translate_message(
            request.customer_message,
            request.shopkeeper_language,
            request.customer_language
        )

        # Shopkeeper reply → Customer language
        shopkeeper_translation = translate_message(
            request.shopkeeper_reply,
            request.customer_language,
            request.shopkeeper_language
        )

        return {
            "status": "success",
            "customer_to_shopkeeper": customer_translation,
            "shopkeeper_to_customer": shopkeeper_translation
        }

    except Exception as e:
        print("CONVERSATION ERROR:", repr(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

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

        speech_result = transcribe_audio(converted_path)

        if speech_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=speech_result["message"]
            )

        transcript = speech_result["transcript"]
        detected_language = speech_result["detected_language"]

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

        speech_result = transcribe_audio(converted_path)

        if speech_result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=speech_result["message"]
            )

        transcript = speech_result["transcript"]
        shopkeeper_detected_language = speech_result["detected_language"]

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


# ==================================================
# SHOP MANAGEMENT API ROUTES
# ==================================================


# --------------------------------------------------
# CUSTOMERS
# --------------------------------------------------

@app.get("/api/customers")
def api_get_customers():
    try:
        customer_rows = get_all_customers()

        result = []

        for customer in customer_rows:
            customer_data = dict(customer)

            balance_data = get_customer_balance(
                customer_data["name"]
            )

            customer_data["balance"] = (
                balance_data["balance"]
                if balance_data
                else 0
            )

            result.append(customer_data)

        return result

    except Exception as e:
        handle_database_error(e)


@app.post("/api/customers")
def api_add_customer(request: CustomerRequest):
    try:
        customer_id = add_customer(request.name.strip())

        return {
            "status": "success",
            "message": "Customer added successfully.",
            "customer_id": customer_id
        }

    except Exception as e:
        handle_database_error(e)


@app.get("/api/customers/{customer_name}/transactions")
def api_get_customer_transactions(customer_name: str):
    try:
        transactions = get_transaction_history(customer_name)

        return serialize_rows(transactions)

    except Exception as e:
        handle_database_error(e)


# --------------------------------------------------
# CUSTOMER KHATA TRANSACTIONS
# --------------------------------------------------

@app.post("/api/khata/transaction")
def api_record_transaction(request: KhataTransactionRequest):
    try:
        transaction_type = request.transaction_type.strip().upper()

        if transaction_type not in ["CREDIT", "PAYMENT"]:
            raise HTTPException(
                status_code=400,
                detail="Transaction type must be CREDIT or PAYMENT."
            )

        result = record_transaction(
            customer_name=request.customer_name.strip(),
            transaction_type=transaction_type,
            amount=request.amount,
            description=request.description.strip()
        )

        return {
            "status": "success",
            "message": result
        }

    except HTTPException:
        raise

    except Exception as e:
        handle_database_error(e)


# --------------------------------------------------
# PRODUCTS AND STOCK
# --------------------------------------------------

@app.get("/api/products")
def api_get_products():
    try:
        return get_all_products()

    except Exception as e:
        handle_database_error(e)


@app.post("/api/products")
def api_add_product(request: ProductRequest):
    try:
        result = add_product(
            name=request.name.strip(),
            price=request.price,
            quantity=request.quantity
        )

        return {
            "status": "success",
            "message": "Product added successfully.",
            "product": result
        }

    except Exception as e:
        handle_database_error(e)


@app.post("/api/stock")
def api_update_stock(request: StockUpdateRequest):
    try:
        result = update_stock(
            product_name=request.product_name.strip(),
            quantity_change=request.quantity_change
        )

        return {
            "status": "success",
            "message": "Stock updated successfully.",
            "result": result
        }

    except Exception as e:
        handle_database_error(e)


# --------------------------------------------------
# SALES
# --------------------------------------------------

@app.post("/api/sales")
def api_record_sale(request: SaleRequest):
    try:
        payment_method = request.payment_method.strip().upper()

        if payment_method not in ["CASH", "UPI", "CARD"]:
            raise HTTPException(
                status_code=400,
                detail="Payment method must be CASH, UPI, or CARD."
            )

        result = record_sale(
            product_name=request.product_name.strip(),
            quantity=request.quantity,
            payment_method=payment_method
        )

        return {
            "status": "success",
            "message": "Sale recorded successfully.",
            "sale": result
        }

    except HTTPException:
        raise

    except Exception as e:
        handle_database_error(e)


# --------------------------------------------------
# EXPENSES
# --------------------------------------------------

@app.get("/api/expenses")
def api_get_expenses():
    try:
        expenses = get_all_expenses()

        return serialize_rows(expenses)

    except Exception as e:
        handle_database_error(e)


@app.post("/api/expenses")
def api_add_expense(request: ExpenseRequest):
    try:
        result = record_expense(
            category=request.category.strip(),
            amount=request.amount,
            description=request.description.strip()
        )

        return {
            "status": "success",
            "message": "Expense recorded successfully.",
            "expense": result
        }

    except Exception as e:
        handle_database_error(e)


# --------------------------------------------------
# DAILY BUSINESS REPORT
# --------------------------------------------------

@app.get("/api/reports/daily")
def api_daily_report():
    try:
        return get_daily_business_summary()

    except Exception as e:
        handle_database_error(e)
