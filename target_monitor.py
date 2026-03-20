import requests
import os

# CONFIG
API_KEY = os.getenv('TARGET_API_KEY', 'ff457966e64d5e877fdbad070f276d18ecec4a01')  # fallback; update if rotated
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')  # required for alerts
STORES = [
    {"id": 2354, "name": "Phoenix Spectrum (85013)", "zip": "85013"},
    {"id": 1242, "name": "Goodyear (85395)", "zip": "85395"}
]
TCINS = ["1009318827", "95082118", "1009818849", "1009818850", "1009790713"]  # Ascended Heroes examples


def check_store(tcin, store_id, zip_code):
    url = f"https://redsky.target.com/redsky_aggregations/v1/web/pdp_fulfillment_v1?key={API_KEY}&tcin={tcin}&store_id={store_id}&zip={zip_code}&is_bot=false"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        fulfillment = data.get("data", {}).get("product", {}).get("fulfillment", {})
        store_opts = fulfillment.get("store_options", [{}])[0]
        status = (
            store_opts.get("order_pickup", {}).get("availability_status")
            or store_opts.get("in_store_only", {}).get("availability_status")
        )
        qty = store_opts.get("location_available_to_promise_quantity", 0)
        return status, qty
    except Exception as e:
        print(f"Error checking {tcin} at {store_id}: {e}")
        return None, 0


print("Running Ascended Heroes restock check...")
alerts = []

for tcin in TCINS:
    for store in STORES:
        status, qty = check_store(tcin, store["id"], store["zip"])
        if status == "IN_STOCK" or qty > 0:
            alert = f"🚨 RESTOCK DETECTED! {tcin} at {store['name']}: {status} (Qty: {qty})"
            alerts.append(alert)
            print(alert)

if alerts and DISCORD_WEBHOOK:
    payload = {"content": "\n".join(alerts)}
    try:
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        print("Discord alert sent!")
    except Exception as e:
        print(f"Failed to send Discord: {e}")
elif alerts:
    print("No Discord webhook set — alerts printed only.")
else:
    print("No stock found this cycle.")
