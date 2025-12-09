#test.py
from datetime import datetime, timezone
from shared_data import SHARED_DATA
import json

hb_interval = 300  # Heartbeat interval in seconds
charger_id = "PL10200787"
vendor = "GRESYSTEM"
model = "CP700P"
unique_id = "12345"

if SHARED_DATA['registered_chargers'][charger_id]['chargePointVendor'] != vendor or SHARED_DATA['registered_chargers'][charger_id]['chargePointModel'] != model:
    print(f"[{charger_id}] BootNotification Rejected: Charger details are not identical")
    error_response = [4, unique_id, "SecurityError", "Charger details are not identical", {}]
    # return json.dumps(error_response)
    print(json.dumps(error_response))

response_payload = {
    "status": "Accepted",
    "currentTime": datetime.now(timezone.utc).isoformat() + "Z",
    "interval": hb_interval
}

print(f"[{charger_id}] BootNotification Accepted: {response_payload}")