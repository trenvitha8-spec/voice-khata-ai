from backend.ledger import (
    record_expense,
    get_today_expenses,
    get_all_expenses
)

print(record_expense("Electricity", 500, "Monthly electricity bill"))
print(record_expense("Transport", 200, "Goods transportation"))

print("Today's expenses:", get_today_expenses())
print("All expenses:", get_all_expenses())
