from fastapi import FastAPI
from contextlib import asynccontextmanager
import requests
import json

API_KEY = "14431d54514c6f3c8fcbfc754b1ac55d"
BASE_URL = "http://api.nessieisreal.com"
OUTPUT_FILE = "new_bill_output.txt"


def create_bill(account_id: str):
    """Crea una nueva factura (bill) para una cuenta existente"""
    url = f"{BASE_URL}/accounts/{account_id}/bills?key={API_KEY}"
    bill_data = {
        "status": "pending",
        "payee": "KLAR",
        "payment_date": "2025-11-05",
        "nickname": "KLAR",
        "payment_amount": 3994.63
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ejecuta tareas al iniciar y cerrar el servidor"""
    print("🚀 Starting bill upload for existing account...")
    account_id = "68fd8b419683f20dd51a4a82"

    bill_resp, bill_sent = create_bill(account_id)
    output = {
        "account_id": account_id,
        "bill": {
            "response": bill_resp,
            "sent": bill_sent
        }
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=4)
    print(f"📄 Bill info saved to {OUTPUT_FILE}")

    yield  # permite que la app corra normalmente

    print("🛑 Server shutting down...")


app = FastAPI(title="Add Bill to Existing Account", lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "New bill created. Check new_bill_output.txt for details."}
