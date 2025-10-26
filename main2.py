# create_new_bill.py
from fastapi import FastAPI
import requests
import json

app = FastAPI(title="Add Bill to Existing Account")

API_KEY = "14431d54514c6f3c8fcbfc754b1ac55d"
BASE_URL = "http://api.nessieisreal.com"
OUTPUT_FILE = "new_bill_output.txt"


def create_bill(account_id: str):
    """Crea una nueva factura (bill) para una cuenta existente"""
    url = f"{BASE_URL}/accounts/{account_id}/bills?key={API_KEY}"
    bill_data = {
        "status": "pending",
        "payee": "Amazon",
        "payment_date": "2025-11-05",
        "nickname": "Prime Purchase",
        "payment_amount": 2500.50
    }

    print(f"📤 Sending new bill to account {account_id} ...")

    try:
        res = requests.post(url, json=bill_data, timeout=10)
        res_json = res.json()
    except Exception as e:
        print("❌ Error creating bill:", e)
        return None, bill_data

    print("Bill response:", res.status_code, res.text)
    if res.status_code in (200, 201):
        print("✅ Bill created successfully!")
        return res_json, bill_data
    else:
        print("⚠️ Bill creation failed.")
        return res_json, bill_data


def save_output(data: dict):
    """Guarda los datos en un archivo txt"""
    try:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Bill data saved to {OUTPUT_FILE}")
    except Exception as e:
        print("❌ Error saving output:", e)


@app.on_event("startup")
def upload_new_bill():
    account_id = "68fd8b419683f20dd51a4a82"  # tu cuenta existente
    print("🚀 Starting bill upload for existing account...")

    bill_resp, bill_sent = create_bill(account_id)

    output = {
        "account_id": account_id,
        "bill": {
            "response": bill_resp,
            "sent": bill_sent
        }
    }

    save_output(output)


@app.get("/")
def root():
    return {"message": "New bill created. Check new_bill_output.txt for details."}
