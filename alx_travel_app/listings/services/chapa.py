import os
import requests

CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")
CHAPA_BASE_URL = os.getenv("CHAPA_BASE_URL", "https://api.chapa.co/v1")

def initiate_chapa_payment(payment):
    url = f"{CHAPA_BASE_URL}/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "amount": str(payment.amount),
        "currency": "ETB",
        "email": payment.user.email,
        "first_name": payment.user.first_name,
        "last_name": payment.user.last_name,
        "tx_ref": payment.booking_reference,
        "callback_url": "http://127.0.0.1:8000/api/payments/verify/",  # 🔹 Add your verify endpoint
        "return_url": "http://127.0.0.1:8000/payment-success/",
        "customization": {
            "title": "ALX Travel Booking Payment",
            "description": f"Payment for booking {payment.booking_reference}"
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    if data.get("status") == "success":
        return data["data"]["checkout_url"], data["data"]["tx_ref"]
    else:
        raise Exception(data.get("message", "Payment initiation failed"))

def verify_chapa_payment(tx_ref):
    url = f"{CHAPA_BASE_URL}/transaction/verify/{tx_ref}"
    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    return response.json()
