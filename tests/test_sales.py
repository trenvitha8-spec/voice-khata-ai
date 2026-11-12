from backend.ledger import record_sale, get_stock, get_today_sales

print(record_sale("Rice", 2))
print("Remaining stock:", get_stock("Rice"))
print("Today's sales:", get_today_sales())
