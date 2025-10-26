# main.py
from fastapi import FastAPI
import requests
from requests.exceptions import RequestException
import json

app = FastAPI(title="Nessie API AutoUploader")

API_KEY = "14431d54514c6f3c8fcbfc754b1ac55d"
BASE_URL = "http://api.nessieisreal.com"
OUTPUT_FILE = "output.txt"


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
        "first_name": "Cyrce",
        "last_name": "Salinas",
        "address": {
            "street_number": "43",
            "street_name": "Albert",
            "city": "CDMX",
            "state": "CDMX",
            "zip": "03560"
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
        "type": "Checking",
        "nickname": "debito",
        "rewards": 0,
        "balance": 100.00
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


def create_loan(account_id: str):
    url = f"{BASE_URL}/accounts/{account_id}/loans?key={API_KEY}"
    loan_data = {
        "type": "home",
        "status": "pending",
        "credit_score": 720,
        "monthly_payment": 150.75,
        "amount": 3000,
        "description": "Loan for demo"
    }
    try:
        res = requests.post(url, json=loan_data, timeout=10)
        res_json = res.json()
    except RequestException as e:
        print("❌ Failed to create loan:", e)
        return None, None
    except ValueError:
        print("❌ Loan response not JSON")
        return None, None

    print("Loan response:", res.status_code, res.text)
    if res.status_code in (200, 201, 202):
        print("✅ Loan created")
        return res_json, loan_data
    return None, loan_data


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

    # 3) Loan
    loan_resp, loan_sent = create_loan(account_id)
    if loan_resp:
        output["loan"] = {"response": loan_resp, "sent": loan_sent}
    else:
        output["loan"] = {"response": None, "sent": loan_sent}
        print("⚠️ Loan creation failed or returned non-201.")

    # 4) Bill
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
