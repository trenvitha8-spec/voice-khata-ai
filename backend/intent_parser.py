
import json
import time
from backend.ai_client import client, MODEL_NAME

SYSTEM_PROMPT = """
You are the multilingual intent parser for Voice Khata AI,
an assistant for Indian kirana shopkeepers.

Understand natural language in:
English, Hindi, Kannada, Telugu, Tamil, Malayalam,
Marathi and mixed-language speech.

Understand different ways of expressing the same request.
Do not depend on fixed commands or exact wording.

SUPPORTED INTENTS:

- record_credit
- record_payment
- check_balance
- record_sale
- check_stock
- record_expense
- daily_summary
- record_purchase
- list_history
- list_products
- list_expenses
- purchase_history
- general_help
- unknown

Return ONLY valid JSON with these fields:

{
    "intent": "record_credit",
    "customer_name": "Ramesh",
    "amount": 340,
    "product_name": null,
    "quantity": null,
    "payment_method": null,
    "category": null,
    "supplier_name": null,
    "unit_price": null,
    "description": null,
    "language": "Hindi",
    "confidence": 0.95,
    "missing_fields": [],
    "clarification_question": null
}

IMPORTANT RULES:

1. Never invent names, amounts, quantities or prices.
2. If essential information is missing, add its field name to missing_fields.
3. For record_purchase, extract supplier_name, product_name,
   quantity and unit_price.
   The quantity field MUST contain only a number, never units
   such as kg, grams, packets or pieces.
   Example: "20 kg rice" must return quantity: 20.
   Preserve the mentioned measurement unit in description.
4. For record_sale, extract product_name and quantity.
5. For record_expense, extract category and amount.
6. For record_credit and record_payment, extract customer_name and amount.
7. For check_balance and list_history, extract customer_name.
8. For check_stock, extract product_name.
9. For an unclear request, use intent "unknown".
10. Preserve customer, supplier and product names as spoken.
11. Understand code-mixed and regional-language expressions.
12. A request such as "I want tomato" is ambiguous.
    Do not assume whether the user wants to check stock,
    purchase tomatoes or record a sale.
13. Never claim that a transaction has been saved.
14. Return JSON only, without Markdown.
15. Use null for fields that are not provided.
16. Use a confidence score between 0 and 1.
17. For list_products, list_expenses, purchase_history
    and daily_summary, no extra information is required.
"""


def parse_intent(user_message: str) -> dict:

    response = None

    # Retry Gemini if the server is temporarily unavailable
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    SYSTEM_PROMPT,
                    "Shopkeeper's message: " + user_message
                ],
                config={
                    "response_mime_type": "application/json"
                }
            )
            break

        except Exception as error:
            error_message = str(error)

            if (
                ("503" in error_message or "UNAVAILABLE" in error_message)
                and attempt < 2
            ):
                print(f"Gemini is busy. Retrying ({attempt + 1}/2)...")
                time.sleep(2 * (attempt + 1))

            else:
                return {
                    "intent": "unknown",
                    "confidence": 0,
                    "missing_fields": [],
                    "clarification_question": (
                        "I'm temporarily unable to process your request. "
                        "Please try again."
                    ),
                    "error": error_message
                }

    try:
        result = json.loads(response.text)

        if not isinstance(result, dict):
            raise ValueError("Response must be a JSON object")

        return result

    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return {
            "intent": "unknown",
            "confidence": 0,
            "missing_fields": [],
            "clarification_question": "Could you please repeat that?",
            "error": str(error)
        }


if __name__ == "__main__":
    message = input("Enter shopkeeper's message: ")

    result = parse_intent(message)

    print("\nAI understood:")
    print(json.dumps(result, indent=4, ensure_ascii=False))
