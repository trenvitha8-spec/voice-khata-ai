from backend.ledger import (
    add_supplier,
    get_all_suppliers,
    record_purchase,
    get_purchase_history,
    get_stock
)

print(add_supplier("Ravi Traders", "9876543210"))

print(record_purchase("Ravi Traders", "Rice", 20, 50))

print("Updated Rice stock:", get_stock("Rice"))

print("Suppliers:", get_all_suppliers())

print("Purchase history:", get_purchase_history())
