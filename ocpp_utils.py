import websocket
import json
import subprocess
from ocpp16.shared_data import OCPP_HOST, OCPP_PORT

def connect_wifi(serialnumber):
    ssid = "gre-"+ serialnumber  # Replace with your WiFi SSID
    password = "G20#RE!10sys&tem*"  # Replace with your WiFi password
    try:
        result = subprocess.run(
            ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
            check=True,
            capture_output=True,
            text=True
        )
        print("WiFi connection OK:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("WiFi connection Failure:", e.stderr)

# 예시 사용
# connect_wifi("MyWiFiSSID", "MySecretPassword")

def get_res_from_ocpp_server(message):
    try:
        ws = websocket.create_connection("ws://127.0.0.1:8003")  # local host and service port
        request_payload = json.dumps(message)
        ws.send(request_payload)

        response = ws.recv()
        data = json.loads(response)
        ws.close()

        # return data.get(data)
        return data
    except Exception as e:
        print("🔧 WebSocket Error:", e)
        return None