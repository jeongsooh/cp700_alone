# shared_data.py
import asyncio
from typing import Dict, Any, Optional

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
        "CHG-TEST-001": {"chargePointVendor": "Test", "chargePointModel": "A1", "connected": False},
        "CHG-TEST-002": {"chargePointVendor": "Test", "chargePointModel": "B2", "connected": False},
        "CHG-TEST-003": {"chargePointVendor": "Test", "chargePointModel": "C2", "connected": False},
        "PL10200787": {"chargePointVendor": "GRESYSTEM", "chargePointModel": "CP700P", "connected": False},
        "JY710102": {"chargePointVendor": "Jinyoung", "chargePointModel": "JY-070-W4", "connected": False}
    },
    "registered_id_tags": {
        "test01": {"status": "Accepted", "expiryDate": "2030-01-01T00:00:00Z"},
        "test02": {"status": "Blocked", "expiryDate": None}
    }
}

class SharedDataManager:
    """
    공유 데이터 저장소(SHARED_DATA)에 대한 스레드 안전 접근을 제공하는 클래스.
    비동기 환경에서 동시성 문제를 방지하기 위해 락(Lock)을 사용합니다.
    """
    def __init__(self):
        # 비동기 환경에서 데이터 무결성을 보장하기 위한 락
        self._lock = asyncio.Lock()
        
    # =======================================================
    # 읽기 기능 (충전기)
    # =======================================================
    
    async def get_charger_info(self, charger_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 충전기의 등록 정보를 읽습니다.
        """
        # 읽기 작업 시에도 락을 사용하여 데이터가 수정되는 것을 방지합니다.
        async with self._lock:
            # 안전하게 복사본을 반환합니다.
            return SHARED_DATA["registered_chargers"].get(charger_id, None)

    async def is_charger_registered(self, charger_id: str) -> bool:
        """
        특정 충전기 ID가 등록되어 있는지 확인합니다.
        """
        # 읽기 작업은 락을 사용하여 안전하게 수행됩니다.
        async with self._lock:
            return charger_id in SHARED_DATA["registered_chargers"]

    # =======================================================
    # 쓰기/업데이트 기능 (충전기)
    # =======================================================

    async def add_or_update_charger(self, charger_id: str, chargePointVendor: str, chargePointModel: str, connected: bool = False) -> None:
        """
        새로운 충전기를 등록하거나 기존 충전기 정보를 업데이트합니다.
        """
        # 쓰기 작업 시에는 반드시 락을 걸어 동시 수정을 막습니다.
        async with self._lock:
            SHARED_DATA["registered_chargers"][charger_id] = {
                "chargePointVendor": chargePointVendor,
                "chargePointModel": chargePointModel,
                "connected": connected
            }
            print(f"[DATA] 충전기 {charger_id} 정보가 업데이트되었습니다.")

    async def update_charger_connection_status(self, charger_id: str, status: bool) -> None:
        """
        충전기의 연결 상태(connected)만 업데이트합니다.
        """
        async with self._lock:
            if charger_id in SHARED_DATA["registered_chargers"]:
                SHARED_DATA["registered_chargers"][charger_id]["connected"] = status
                print(f"[DATA] 충전기 {charger_id}의 연결 상태가 {status}로 업데이트되었습니다.")
            else:
                print(f"[ERROR] 충전기 {charger_id}는 등록되지 않았습니다. 상태 업데이트 실패.")

    # =======================================================
    # ID Tag 읽기 기능
    # =======================================================
    
    async def get_idtag_info(self, id_tag: str) -> Optional[Dict[str, Any]]:
        """
        특정 ID Tag의 등록 정보를 읽습니다.
        """
        async with self._lock:
            return SHARED_DATA["registered_id_tags"].get(id_tag, None)


# 매니저 객체 생성 (전역적으로 하나의 인스턴스만 사용)
# data_manager = SharedDataManager()

# =======================================================
# 사용 예시 (테스트)
# =======================================================
# async def test_manager():
#     # 1. 특정 충전기가 등록되어 있는지 확인
#     charger_id_a = "PL0787"
#     charger_id_b = "UNKNOWN-001"
    
#     is_a_registered = await data_manager.is_charger_registered(charger_id_a)
#     print(f"충전기 {charger_id_a} 등록 여부: {is_a_registered}") # True
    
#     is_b_registered = await data_manager.is_charger_registered(charger_id_b)
#     print(f"충전기 {charger_id_b} 등록 여부: {is_b_registered}") # False
    
#     # 2. 충전기 정보 읽기
#     info_a = await data_manager.get_charger_info(charger_id_a)
#     print(f"충전기 {charger_id_a} 정보: {info_a}")
    
#     # 3. 새로운 충전기 추가/업데이트
#     new_charger_id = "NEW-CHG-999"
#     await data_manager.add_or_update_charger(new_charger_id, "NewchargePointVendor", "SuperchargePointModel")
    
#     # 4. 업데이트된 정보 확인
#     info_new = await data_manager.get_charger_info(new_charger_id)
#     print(f"새로 추가된 충전기 정보: {info_new}")
    
#     # 5. 연결 상태 업데이트
#     await data_manager.update_charger_connection_status(charger_id_a, True)
#     updated_info_a = await data_manager.get_charger_info(charger_id_a)
#     print(f"연결 상태 업데이트 후 {charger_id_a} 정보: {updated_info_a}")

# 이 코드를 직접 실행하려면 아래 주석을 해제하세요.
# if __name__ == "__main__":
#     asyncio.run(test_manager())