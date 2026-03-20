import os
import requests

# CONFIG
API_KEY = os.getenv("TARGET_API_KEY", "9f36aeafbe60771e321a7cc95a78140772ab3e96")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

STORES = [
    {"id": 2354, "name": "Phoenix Spectrum (85013)", "zip": "85013"},
    {"id": 1242, "name": "Goodyear (85395)", "zip": "85395"},
]

TCINS = [
    "1010148053",  # Ascended Heroes ETB
    "1009318827",
    "95082118",
    "1009818849",
    "1009818850",
    "1009790713",
]


def check_store(tcin, store_id, zip_code):
    url = (
        "https://redsky.target.com/redsky_aggregations/v1/web/"
        "product_fulfillment_and_variation_hierarchy_v1"
        f"?key={API_KEY}"
        f"&required_store_id={store_id}"
        f"&scheduled_delivery_store_id={store_id}"
        f"&store_id={store_id}"
        "&state=AZ"
        f"&zip={zip_code}"
        f"&tcin={tcin}"
        "&channel=WEB"
        f"&page=%2Fp%2FA-{tcin}"
        "&is_bot=false"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://www.target.com",
        "Referer": f"https://www.target.com/p/-/A-{tcin}",
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        fulfillment = data.get("data", {}).get("product", {}).get("fulfillment", {})
        store_options = fulfillment.get("store_options", [])

        if not store_options:
            return None, None, 0, fulfillment.get("shipping_options", {}).get("availability_status")

        store_opt = store_options[0]
        pickup_status = store_opt.get("order_pickup", {}).get("availability_status")
        in_store_status = store_opt.get("in_store_only", {}).get("availability_status")
        qty = store_opt.get("location_available_to_promise_quantity", 0)

        shipping_status = fulfillment.get("shipping_options", {}).get("availability_status")

        return pickup_status, in_store_status, qty, shipping_status

    except Exception as e:
        print(f"Error checking {tcin} at store {store_id}: {e}")
        return None, None, 0, None


print("Running Target restock check...")
alerts = []

for tcin in TCINS:
    for store in STORES:
        pickup_status, in_store_status, qty, shipping_status = check_store(
            tcin, store["id"], store["zip"]
        )

        print(
            f"TCIN {tcin} | {store['name']} | "
            f"pickup={pickup_status} | in_store={in_store_status} | qty={qty} | shipping={shipping_status}"
        )

        in_person_stock = (
            pickup_status == "IN_STOCK"
            or in_store_status == "IN_STOCK"
            or (qty is not None and qty > 0)
        )

        if in_person_stock:
            alert = (
                f"🚨 TARGET RESTOCK DETECTED\n"
                f"TCIN: {tcin}\n"
                f"Store: {store['name']}\n"
                f"Pickup: {pickup_status}\n"
                f"In-Store: {in_store_status}\n"
                f"Qty: {qty}\n"
                f"URL: https://www.target.com/p/-/A-{tcin}"
            )
            alerts.append(alert)
            print(alert)

if alerts and DISCORD_WEBHOOK:
    payload = {"content": "\n\n".join(alerts)}
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        print("Discord alert sent!")
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")
elif alerts:
    print("Alerts found, but no Discord webhook is set.")
else:
    print("No in-person stock found this cycle.")
