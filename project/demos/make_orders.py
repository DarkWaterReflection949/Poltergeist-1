"""Regenerates demos/orders.csv (40 fake Indian e-commerce orders, fixed seed)."""
import csv
import random
import unicodedata
from datetime import date, timedelta

rng = random.Random(50)
FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Karthik", "Meera", "Arjun", "Divya",
         "Rahul", "Kavya", "Siddharth", "Isha", "Nikhil", "Pooja", "Aditya", "Neha", "Varun", "Tanvi"]
LAST = ["Sharma", "Iyer", "Reddy", "Nair", "Mehta", "Gupta", "Rao", "Patel", "Das", "Menon", "Singh", "Kulkarni"]
ACCENTED = ["Ren\u00e9e Fernandes", "Jos\u00e9 Almeida", "Ana\u00efs D'Souza", "Zo\u00eb Pereira", "Andr\u00e9 Lobo"]
CITIES = ["Bengaluru", "Mumbai", "Pune", "Chennai", "Hyderabad", "Delhi", "Kolkata", "Jaipur"]

names = set(ACCENTED)
while len(names) < 40:
    names.add(f"{rng.choice(FIRST)} {rng.choice(LAST)}")
names = sorted(names)
rng.shuffle(names)

rows = []
for i, name in enumerate(names, start=1):
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    email = ascii_name.replace(" ", ".").replace("'", "") + "@example.com"
    rows.append({
        "order_id": f"ORD-{i:04d}",
        "customer_id": f"{rng.randint(100, 9999):05d}",
        "customer": name,
        "email": email,
        "phone": str(rng.randint(6, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(9)),
        "city": rng.choice(CITIES),
        "order_date": (date(2026, 1, 1) + timedelta(days=rng.randint(0, 270))).isoformat(),
        "amount": f"{rng.uniform(150, 45000):.2f}",
        "quantity": str(rng.randint(1, 9)),
    })

with open("demos/orders.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print("wrote demos/orders.csv with", len(rows), "rows")
