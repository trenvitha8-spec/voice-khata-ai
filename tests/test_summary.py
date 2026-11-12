from backend.ledger import get_daily_business_summary

print("DAILY SHOP SUMMARY")
print("------------------")

summary = get_daily_business_summary()

for key, value in summary.items():
    print(f"{key}: {value}")
