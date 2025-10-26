# main.py
from fastapi import FastAPI
import requests
from requests.exceptions import RequestException
import json

app = FastAPI(title="Nessie API AutoUploader")

API_KEY = "14431d54514c6f3c8fcbfc754b1ac55d"
BASE_URL = "http://api.nessieisreal.com"
OUTPUT_FILE = "output2.txt"


def safe_extract_id(resp_json: dict):
    """Extrae un _id de la respuesta JSON de Nessie."""
    if not isinstance(resp_json, dict):
        return None
    if "_id" in resp_json:
        return resp_json["_id"]
    if "objectCreated" in resp_json and isinstance(resp_json["objectCreated"], dict):
        return resp_json["objectCreated"].get("_id")
    for v in resp_json.values():
        if isinstance(v, dict) and "_id" in v:
            return v["_id"]
    return None


def create_customer(): #✅
    url = f"{BASE_URL}/customers?key={API_KEY}"
    customer_data = {
        "first_name": "Cyrce D",
        "last_name": "Salinas Rojas",
        "address": {
            "street_number": "2208",
            "street_name": "C Playa Revolcadero",
            "city": "Monterrey",
            "state": "TX",
            "zip": "64821"
        }
    }
    try:
        res = requests.post(url, json=customer_data, timeout=10)
        res_json = res.json()
    except RequestException as e:
        print("❌ Failed to create customer:", e)
        return None, None
    except ValueError:
        print("❌ Customer response not JSON")
        return None, None

    cust_id = safe_extract_id(res_json)
    print("Customer response:", res.status_code, res.text)
    if cust_id:
        print("✅ Customer created with id:", cust_id)
        return cust_id, customer_data
    return None, None


def create_account(customer_id: str):
    url = f"{BASE_URL}/customers/{customer_id}/accounts?key={API_KEY}"
    account_data = {
        "type": "Credit Card",
        "nickname": "My Credit Card",
        "rewards": 0,
        "balance": 0
    }
    try:
        res = requests.post(url, json=account_data, timeout=10)
        res_json = res.json()
    except RequestException as e:
        print("❌ Failed to create account:", e)
        return None, None
    except ValueError:
        print("❌ Account response not JSON")
        return None, None

    acct_id = safe_extract_id(res_json)
    print("Account response:", res.status_code, res.text)
    if acct_id:
        print("✅ Account created with id:", acct_id)
        return acct_id, account_data
    return None, None


def create_bill(account_id: str):
    url = f"{BASE_URL}/accounts/{account_id}/bills?key={API_KEY}"
    bill_data = {
        "status": "pending",
        "payee": "Banamex",
        "payment_date": "2025-10-05",
        "nickname": "Costco Banamex",
        "payment_amount": 5710.00,
    }
    try:
        res = requests.post(url, json=bill_data, timeout=10)
        res_json = res.json()
    except RequestException as e:
        print("❌ Failed to create bill:", e)
        return None, None
    except ValueError:
        print("❌ Bill response not JSON")
        return None, None

    print("Bill response:", res.status_code, res.text)
    if res.status_code in (200, 201, 202):
        print("✅ Bill created")
        return res_json, bill_data
    return None, bill_data


def save_output(data: dict):
    """Guarda los datos en output.txt"""
    try:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Data saved to {OUTPUT_FILE}")
    except Exception as e:
        print("❌ Failed to save output:", e)


@app.on_event("startup")
def auto_upload():
    """Ejecuta todo el flujo al iniciar FastAPI"""
    print("🚀 Starting automatic upload to Nessie API...")

    output = {}

    # 1) Customer
    customer_id, customer_sent = create_customer()
    if not customer_id:
        print("❌ Customer creation failed")
        return
    output["customer"] = {"id": customer_id, "sent": customer_sent}

    # 2) Account
    account_id, account_sent = create_account(customer_id)
    if not account_id:
        print("❌ Account creation failed")
        return
    output["account"] = {"id": account_id, "sent": account_sent}


    # 3) Bill
    bill_resp, bill_sent = create_bill(account_id)
    if bill_resp:
        output["bill"] = {"response": bill_resp, "sent": bill_sent}
    else:
        output["bill"] = {"response": None, "sent": bill_sent}
        print("⚠️ Bill creation failed or returned non-201.")

    # 5) Guardar todo en un archivo txt
    save_output(output)

    print("✅ Auto upload completed.")


@app.get("/")
def root():
    return {"message": "Auto upload executed at startup. Check output.txt for results."}
