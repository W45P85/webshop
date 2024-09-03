import requests
from django.conf import settings

def send_package_with_dhl(order):
    url = "https://api-sandbox.dhl.com"  # Sandbox-URL zum Testen (Senden der Lieferung)
    # url = "https://api.dhl.com" # Produktiv-URL (Senden der Lieferung)
    headers = {
        "Authorization": f"Bearer {settings.DHL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        # Beispiel-Payload, je nach DHL-API-Dokumentation anpassen
        "order_id": order.id,
        "address": order.shipping_address,
        "weight": order.weight,
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return True
    else:
        return False
