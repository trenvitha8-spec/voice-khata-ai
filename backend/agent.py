
import math

from backend.intent_parser import parse_intent
from backend import ledger


def is_valid_number(value):
    if isinstance(value, bool):
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def format_currency(value):
    return f"₹{float(value):,.2f}"


def create_pending_action(action, data, message):
    return {
        "status": "confirmation_required",
        "message": message + " Please say yes to confirm or no to cancel.",
        "pending_action": {
            "action": action,
            "data": data
        }
    }


def process_message(message):

    if not message or not message.strip():
        return {
            "status": "needs_clarification",
            "message": "Please tell me what you need help with."
        }

    intent_data = parse_intent(message)

    if not isinstance(intent_data, dict):
        return {
            "status": "error",
            "message": "I couldn't understand your request."
        }

    intent = intent_data.get("intent", "unknown")

    try:
        confidence = float(intent_data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0

    if confidence < 0.70:
        return {
            "status": "needs_clarification",
            "message": (
                intent_data.get("clarification_question")
                or "Could you please explain that again?"
            )
        }

    if intent_data.get("missing_fields"):
        return {
            "status": "needs_clarification",
            "message": (
                intent_data.get("clarification_question")
                or "I need some more information."
            )
        }

    # RECORD CREDIT
    if intent == "record_credit":

        customer = intent_data.get("customer_name")
        amount = intent_data.get("amount")

        if not isinstance(customer, str) or not customer.strip():
            return {
                "status": "needs_clarification",
                "message": "Whose credit should I record?"
            }

        if not is_valid_number(amount) or float(amount) <= 0:
            return {
                "status": "needs_clarification",
                "message": "Please provide a valid credit amount."
            }

        return create_pending_action(
            "record_credit",
            {
                "customer_name": customer.strip(),
                "amount": float(amount),
                "description": intent_data.get("description") or ""
            },
            f"Record {format_currency(amount)} as credit for {customer}?"
        )

    # RECORD PAYMENT
    elif intent == "record_payment":

        customer = intent_data.get("customer_name")
        amount = intent_data.get("amount")

        if not isinstance(customer, str) or not customer.strip():
            return {
                "status": "needs_clarification",
                "message": "Who made the payment?"
            }

        if not is_valid_number(amount) or float(amount) <= 0:
            return {
                "status": "needs_clarification",
                "message": "Please provide a valid payment amount."
            }

        return create_pending_action(
            "record_payment",
            {
                "customer_name": customer.strip(),
                "amount": float(amount),
                "description": intent_data.get("description") or ""
            },
            f"Record {format_currency(amount)} payment from {customer}?"
        )

    # CHECK BALANCE
    elif intent == "check_balance":

        customer = intent_data.get("customer_name")

        if not isinstance(customer, str) or not customer.strip():
            return {
                "status": "needs_clarification",
                "message": "Whose balance should I check?"
            }

        balance = ledger.get_customer_balance(customer.strip())

        return {
            "status": "success",
            "message": f"{customer}'s current balance is {format_currency(balance)}.",
            "data": {
                "customer": customer,
                "balance": balance
            }
        }

    # RECORD SALE
    elif intent == "record_sale":

        product = intent_data.get("product_name")
        quantity = intent_data.get("quantity")
        payment_method = (
            intent_data.get("payment_method") or "CASH"
        ).upper()

        if not isinstance(product, str) or not product.strip():
            return {
                "status": "needs_clarification",
                "message": "Which product did you sell?"
            }

        if (
            not is_valid_number(quantity)
            or float(quantity) <= 0
            or not float(quantity).is_integer()
        ):
            return {
                "status": "needs_clarification",
                "message": "Please provide a valid sale quantity."
            }

        if payment_method not in ("CASH", "UPI", "CARD"):
            return {
                "status": "needs_clarification",
                "message": "Was the payment made by cash, UPI or card?"
            }

        return create_pending_action(
            "record_sale",
            {
                "product_name": product.strip(),
                "quantity": int(quantity),
                "payment_method": payment_method
            },
            f"Record a sale of {int(quantity)} {product} using {payment_method}?"
        )

    # CHECK STOCK
    elif intent == "check_stock":

        product = intent_data.get("product_name")

        if not isinstance(product, str) or not product.strip():
            return {
                "status": "needs_clarification",
                "message": "Which product's stock should I check?"
            }

        stock = ledger.get_stock(product.strip())

        if stock is None:
            return {
                "status": "not_found",
                "message": f"I couldn't find {product} in your product list."
            }

        return {
            "status": "success",
            "message": (
                f"{stock['name']} has {stock['quantity']} units in stock. "
                f"Price: {format_currency(stock['price'])} per unit."
            ),
            "data": stock
        }

    # RECORD EXPENSE
    elif intent == "record_expense":

        category = intent_data.get("category")
        amount = intent_data.get("amount")
        description = intent_data.get("description") or ""

        if not isinstance(category, str) or not category.strip():
            return {
                "status": "needs_clarification",
                "message": "What type of expense should I record?"
            }

        if not is_valid_number(amount) or float(amount) <= 0:
            return {
                "status": "needs_clarification",
                "message": "Please provide a valid expense amount."
            }

        return create_pending_action(
            "record_expense",
            {
                "category": category.strip(),
                "amount": float(amount),
                "description": description
            },
            f"Record {format_currency(amount)} as {category} expense?"
        )

    # RECORD PURCHASE
    elif intent == "record_purchase":

        supplier = intent_data.get("supplier_name")
        product = intent_data.get("product_name")
        quantity = intent_data.get("quantity")
        unit_price = intent_data.get("unit_price")

        if not isinstance(supplier, str) or not supplier.strip():
            return {
                "status": "needs_clarification",
                "message": "Which supplier did you purchase from?"
            }

        if not isinstance(product, str) or not product.strip():
            return {
                "status": "needs_clarification",
                "message": "Which product did you purchase?"
            }

        if (
            not is_valid_number(quantity)
            or float(quantity) <= 0
            or not float(quantity).is_integer()
        ):
            return {
                "status": "needs_clarification",
                "message": "Please provide a valid purchase quantity."
            }

        if not is_valid_number(unit_price) or float(unit_price) < 0:
            return {
                "status": "needs_clarification",
                "message": "Please provide the purchase price per unit."
            }

        total = int(quantity) * float(unit_price)

        return create_pending_action(
            "record_purchase",
            {
                "supplier_name": supplier.strip(),
                "product_name": product.strip(),
                "quantity": int(quantity),
                "unit_price": float(unit_price)
            },
            (
                f"Purchase {int(quantity)} {product} from {supplier} "
                f"at {format_currency(unit_price)} per unit? "
                f"Total: {format_currency(total)}."
            )
        )

    # DAILY SUMMARY
    elif intent == "daily_summary":

        summary = ledger.get_daily_business_summary()

        return {
            "status": "success",
            "message": "Here is your daily business summary.",
            "data": summary
        }

    # CUSTOMER TRANSACTION HISTORY
    elif intent == "list_history":

        customer = intent_data.get("customer_name")

        if not isinstance(customer, str) or not customer.strip():
            return {
                "status": "needs_clarification",
                "message": "Whose transaction history should I show?"
            }

        history = ledger.get_transaction_history(customer.strip())

        return {
            "status": "success",
            "message": f"Transaction history for {customer}.",
            "data": [dict(row) for row in history]
        }

    # LIST PRODUCTS
    elif intent == "list_products":

        products = ledger.get_all_products()

        return {
            "status": "success",
            "message": f"You have {len(products)} products in your shop.",
            "data": products
        }

    # LIST EXPENSES
    elif intent == "list_expenses":

        expenses = ledger.get_all_expenses()

        return {
            "status": "success",
            "message": f"Found {len(expenses)} expense records.",
            "data": expenses
        }

    # PURCHASE HISTORY
    elif intent == "purchase_history":

        purchases = ledger.get_purchase_history()

        return {
            "status": "success",
            "message": f"Found {len(purchases)} purchase records.",
            "data": purchases
        }

    # GENERAL HELP
    elif intent == "general_help":

        return {
            "status": "success",
            "message": (
                "Hello! I am Voice Khata AI. I can record credit, "
                "payments, sales, purchases and expenses. "
                "I can also check customer balances, product stock, "
                "transaction history and daily business summaries."
            )
        }

    # UNKNOWN
    else:

        return {
            "status": "needs_clarification",
            "message": (
                intent_data.get("clarification_question")
                or "I didn't understand. Could you please explain?"
            )
        }


# CONFIRM OR CANCEL ACTION
def confirm_action(pending_action, confirmed):

    if not confirmed:
        return {
            "status": "cancelled",
            "message": "Okay. No changes have been made."
        }

    if not isinstance(pending_action, dict):
        return {
            "status": "error",
            "message": "Invalid action. Please try again."
        }

    action = pending_action.get("action")
    data = pending_action.get("data")

    if not isinstance(data, dict):
        return {
            "status": "error",
            "message": "Invalid action details."
        }

    try:

        if action == "record_credit":

            result = ledger.record_transaction(
                data["customer_name"],
                "CREDIT",
                data["amount"],
                data.get("description", "")
            )

            message = (
                f"Credit of {format_currency(data['amount'])} "
                f"recorded for {data['customer_name']}."
            )

        elif action == "record_payment":

            result = ledger.record_transaction(
                data["customer_name"],
                "PAYMENT",
                data["amount"],
                data.get("description", "")
            )

            message = (
                f"Payment of {format_currency(data['amount'])} "
                f"recorded for {data['customer_name']}."
            )

        elif action == "record_sale":

            result = ledger.record_sale(
                data["product_name"],
                data["quantity"],
                data["payment_method"]
            )

            message = (
                f"Sale recorded: {result['quantity_sold']} "
                f"{result['product']} for {format_currency(result['total'])}. "
                f"Remaining stock: {result['remaining_stock']}."
            )

        elif action == "record_expense":

            result = ledger.record_expense(
                data["category"],
                data["amount"],
                data.get("description", "")
            )

            message = (
                f"Expense of {format_currency(data['amount'])} "
                f"recorded under {data['category']}."
            )

        elif action == "record_purchase":

            result = ledger.record_purchase(
                data["supplier_name"],
                data["product_name"],
                data["quantity"],
                data["unit_price"]
            )

            message = (
                f"Purchase recorded: {result['quantity_purchased']} "
                f"{result['product']} from {result['supplier']}. "
                f"Total: {format_currency(result['total_amount'])}."
            )

        else:
            return {
                "status": "error",
                "message": "This action is not allowed."
            }

        return {
            "status": "success",
            "message": message,
            "data": result
        }

    except (ValueError, KeyError, TypeError) as error:

        return {
            "status": "error",
            "message": str(error)
        }

    except Exception:

        return {
            "status": "error",
            "message": (
                "Something went wrong while saving. "
                "Please check your records before retrying."
            )
        }


# COMMAND LINE TEST
if __name__ == "__main__":

    message = input("Shopkeeper: ")

    response = process_message(message)

    print("\nVoice Khata AI:")
    print(response)

    if response.get("status") == "confirmation_required":

        answer = input("\nConfirm? (yes/no): ").strip().lower()

        result = confirm_action(
            response["pending_action"],
            answer in ("yes", "y")
        )

        print("\nFinal result:")
        print(result)
