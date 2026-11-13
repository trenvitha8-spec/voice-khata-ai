
import os
import json
import re
import urllib.request
import urllib.parse
from dotenv import load_dotenv

load_dotenv(override=True)

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

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "te": "Telugu",
    "ta": "Tamil",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
}

# Starter grocery dictionary.
# Each product contains its name in all 10 supported languages.
GROCERY_DICTIONARY = {
    "rice": {
        "en": "rice",
        "hi": "चावल",
        "kn": "ಅಕ್ಕಿ",
        "te": "బియ్యం",
        "ta": "அரிசி",
        "ml": "അരി",
        "mr": "तांदूळ",
        "bn": "চাল",
        "gu": "ચોખા",
        "pa": "ਚੌਲ",
    },
    "wheat_flour": {
        "en": "wheat flour",
        "hi": "गेहूं का आटा",
        "kn": "ಗೋಧಿ ಹಿಟ್ಟು",
        "te": "గోధుమ పిండి",
        "ta": "கோதுமை மாவு",
        "ml": "ഗോതമ്പ് പൊടി",
        "mr": "गव्हाचे पीठ",
        "bn": "গমের আটা",
        "gu": "ઘઉંનો લોટ",
        "pa": "ਕਣਕ ਦਾ ਆਟਾ",
    },
    "sugar": {
        "en": "sugar",
        "hi": "चीनी",
        "kn": "ಸಕ್ಕರೆ",
        "te": "చక్కెర",
        "ta": "சர்க்கரை",
        "ml": "പഞ്ചസാര",
        "mr": "साखर",
        "bn": "চিনি",
        "gu": "ખાંડ",
        "pa": "ਖੰਡ",
    },
    "salt": {
        "en": "salt",
        "hi": "नमक",
        "kn": "ಉಪ್ಪು",
        "te": "ఉప్పు",
        "ta": "உப்பு",
        "ml": "ഉപ്പ്",
        "mr": "मीठ",
        "bn": "লবণ",
        "gu": "મીઠું",
        "pa": "ਨਮਕ",
    },
    "cooking_oil": {
        "en": "cooking oil",
        "hi": "खाने का तेल",
        "kn": "ಅಡುಗೆ ಎಣ್ಣೆ",
        "te": "వంట నూనె",
        "ta": "சமையல் எண்ணெய்",
        "ml": "പാചക എണ്ണ",
        "mr": "स्वयंपाकाचे तेल",
        "bn": "রান্নার তেল",
        "gu": "રસોઈનું તેલ",
        "pa": "ਖਾਣਾ ਪਕਾਉਣ ਦਾ ਤੇਲ",
    },
    "dal": {
        "en": "dal",
        "hi": "दाल",
        "kn": "ಬೇಳೆ",
        "te": "పప్పు",
        "ta": "பருப்பு",
        "ml": "പരിപ്പ്",
        "mr": "डाळ",
        "bn": "ডাল",
        "gu": "દાળ",
        "pa": "ਦਾਲ",
    },
    "chickpeas": {
        "en": "chickpeas",
        "hi": "चना",
        "kn": "ಕಡಲೆ",
        "te": "శనగలు",
        "ta": "கொண்டைக்கடலை",
        "ml": "കടല",
        "mr": "हरभरा",
        "bn": "ছোলা",
        "gu": "ચણા",
        "pa": "ਛੋਲੇ",
    },
    "tea": {
        "en": "tea",
        "hi": "चाय",
        "kn": "ಚಹಾ",
        "te": "టీ",
        "ta": "தேநீர்",
        "ml": "ചായ",
        "mr": "चहा",
        "bn": "চা",
        "gu": "ચા",
        "pa": "ਚਾਹ",
    },
    "coffee": {
        "en": "coffee",
        "hi": "कॉफी",
        "kn": "ಕಾಫಿ",
        "te": "కాఫీ",
        "ta": "காபி",
        "ml": "കാപ്പി",
        "mr": "कॉफी",
        "bn": "কফি",
        "gu": "કૉફી",
        "pa": "ਕੌਫੀ",
    },
    "turmeric": {
        "en": "turmeric",
        "hi": "हल्दी",
        "kn": "ಅರಿಶಿನ",
        "te": "పసుపు",
        "ta": "மஞ்சள்",
        "ml": "മഞ്ഞൾ",
        "mr": "हळद",
        "bn": "হলুদ",
        "gu": "હળદર",
        "pa": "ਹਲਦੀ",
    },
    "chilli_powder": {
        "en": "chilli powder",
        "hi": "मिर्च पाउडर",
        "kn": "ಮೆಣಸಿನ ಪುಡಿ",
        "te": "కారం పొడి",
        "ta": "மிளகாய்த்தூள்",
        "ml": "മുളകുപൊടി",
        "mr": "तिखट",
        "bn": "লঙ্কার গুঁড়ো",
        "gu": "મરચું પાવડર",
        "pa": "ਲਾਲ ਮਿਰਚ ਪਾਊਡਰ",
    },
    "coriander_powder": {
        "en": "coriander powder",
        "hi": "धनिया पाउडर",
        "kn": "ಕೊತ್ತಂಬರಿ ಪುಡಿ",
        "te": "ధనియాల పొడి",
        "ta": "கொத்தமல்லித்தூள்",
        "ml": "മല്ലിപ്പൊടി",
        "mr": "धणेपूड",
        "bn": "ধনে গুঁড়ো",
        "gu": "ધાણા પાવડર",
        "pa": "ਧਨੀਆ ਪਾਊਡਰ",
    },
}
GROCERY_ALIASES = {
    "rice": {
        "kn": ["ಅನ್ನ"]
    }
}


def normalize_language(language):
    language = language.lower().strip()

    if language in LANGUAGE_CODES:
        return LANGUAGE_CODES[language]

    code = language.split("-")[0]

    if code in LANGUAGE_CODES.values():
        return code

    raise ValueError(f"Unsupported language: {language}")


def contains_term(text, term):
    if re.fullmatch(r"[a-zA-Z0-9 ]+", term):
        return re.search(
            r"(?<!\w)" + re.escape(term) + r"(?!\w)",
            text,
            re.IGNORECASE
        ) is not None

    return term.casefold() in text.casefold()


def replace_term(text, old_term, new_term):
    if re.fullmatch(r"[a-zA-Z0-9 ]+", old_term):
        return re.sub(
            r"(?<!\w)" + re.escape(old_term) + r"(?!\w)",
            lambda match: new_term,
            text,
            flags=re.IGNORECASE
        )

    return text.replace(old_term, new_term)


def protect_grocery_terms(original_text, translated_text,
                          source_code, target_code):

    if source_code == "autodetect":
        return translated_text

    for product_name, product in GROCERY_DICTIONARY.items():
        source_term = product[source_code]
        target_term = product[target_code]

        if contains_term(original_text, source_term):

            for language_code, term in product.items():
                if language_code != target_code:
                    translated_text = replace_term(
                        translated_text, term, target_term
                    )

            aliases = GROCERY_ALIASES.get(
                product_name, {}
            ).get(target_code, [])

            for alias in aliases:
                translated_text = replace_term(
                    translated_text, alias, target_term
                )

    return translated_text.strip()
def translate_with_bodhan(text, target_code):

    api_key = os.getenv("BODHAN_API_KEY")

    if not api_key:
        raise RuntimeError("BODHAN_API_KEY is missing")

    payload = {
        "model": "indic-translate",
        "messages": [
            {
                "role": "user",
                "content": text
            }
        ],
        "target_language_code": target_code
    }

    request = urllib.request.Request(
        "https://api.bodhan.ai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    translated_text = data["choices"][0]["message"]["content"].strip()

    if not translated_text:
        raise RuntimeError("Bodhan returned an empty translation")

    return translated_text


def translate_with_mymemory(text, target_code, source_code):

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
        raise RuntimeError(
            data.get("responseDetails", "MyMemory translation failed")
        )

    return data["responseData"]["translatedText"]


def translate_message(text, target_language, source_language=None):

    if not text or not text.strip():
        raise ValueError("Message cannot be empty")

    if source_language and source_language.strip().lower() not in [
        "auto-detect", "autodetect", "auto"
    ]:
        source_code = normalize_language(source_language)
    else:
        source_code = "autodetect"

    target_code = normalize_language(target_language)

    try:
        translated_text = translate_with_bodhan(text, target_code)
        engine = "Bodhan AI"

    except Exception as bodhan_error:
        print("BODHAN ERROR:", repr(bodhan_error))
        print("Trying MyMemory fallback...")

        translated_text = translate_with_mymemory(
            text, target_code, source_code
        )
        engine = "MyMemory"

    if source_code != "autodetect":
        translated_text = protect_grocery_terms(
            text,
            translated_text,
            source_code,
            target_code
        )

    print("Translation engine used:", engine)

    return translated_text


def translate_detected_message(
    text,
    detected_language,
    target_language=None
):
    try:
        if target_language is None:
            target_language = detected_language

        translated_text = translate_message(
            text,
            target_language,
            detected_language
        )

        return {
            "status": "success",
            "translated_message": translated_text
        }

    except Exception as error:
        print("TRANSLATION ERROR:", repr(error))

        return {
            "status": "error",
            "message": str(error)
        }
