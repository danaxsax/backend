import os 
import requests
from requests.exceptions import RequestException


API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

def create_customer(
        name: str ,
        
): #✅
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