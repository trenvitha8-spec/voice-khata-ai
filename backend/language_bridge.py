
import urllib.request
import urllib.parse
import json

LANGUAGE_CODES = {
    "english": "en",
    "hindi": "hi",
    "kannada": "kn",
    "telugu": "te",
    "tamil": "ta",
    "malayalam": "ml",
    "marathi": "mr",
    "bengali": "bn",
    "gujarati": "gu",
    "punjabi": "pa",
}


def normalize_language(language):
    language = language.lower().strip()

    if language in LANGUAGE_CODES:
        return LANGUAGE_CODES[language]

    code = language.split("-")[0]

    if code in LANGUAGE_CODES.values():
        return code

    raise ValueError(f"Unsupported language: {language}")


def translate_message(text, target_language):
    source_code = "autodetect"
    target_code = normalize_language(target_language)

    params = urllib.parse.urlencode({
        "q": text,
        "langpair": f"{source_code}|{target_code}"
    })

    url = "https://api.mymemory.translated.net/get?" + params

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "VoiceKhataAI/1.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("responseStatus") != 200:
        raise RuntimeError(data.get("responseDetails", "Translation failed"))

    return data["responseData"]["translatedText"]


def translate_detected_message(text, detected_language, target_language=None):
    try:
        if target_language is None:
            target_language = detected_language

        translated_text = translate_message(text, target_language)

        return {
            "status": "success",
            "translated_message": translated_text
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }