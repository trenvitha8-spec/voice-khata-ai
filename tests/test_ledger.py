from backend.database import initialize_database
from backend.ledger import record_transaction, get_customer_balance

initialize_database()

print(record_transaction("Suresh", "CREDIT", 500))
print(record_transaction("Suresh", "PAYMENT", 200))
print("Customer balance:", get_customer_balance("Suresh"))
