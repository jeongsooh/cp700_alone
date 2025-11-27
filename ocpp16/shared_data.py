# shared_data.py
import asyncio

# --- OCPP 서버 설정 ---
OCPP_HOST = '127.0.0.1'
OCPP_PORT = 443
CHARGER_ID = 'CHG-TEST-001' # 서버에 전송될 충전기 ID
OCPP_URI = f'wss://{OCPP_HOST}:{OCPP_PORT}/openocpp/{CHARGER_ID}'
CERT_FILE = 'certificate/cert.pem' 
KEY_FILE = 'certificate/key.pem'
HB_INTERVAL = 180 # Heartbeat 주기 (초)
FLASK_PORT = 5000

# --- 💾 공유 데이터 저장소 (DB 대체) ---
SHARED_DATA = {
    "registered_chargers": {
        "CHG-TEST-001": {"vendor": "Test", "model": "A1"},
        "CHG-TEST-002": {"vendor": "Test", "model": "B2"},
        "CHG-TEST-003": {"vendor": "Test", "model": "C2"}
    },
    "registered_id_tags": {
        "test01": {"status": "Accepted", "expiryDate": "2030-01-01T00:00:00Z"},
        "test02": {"status": "Blocked", "expiryDate": None}
    }
}