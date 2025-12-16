# ocpp_message.py
import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from ocpp16.data_manager import JsonConfigManager
from ocpp16.shared_data import ENERGY_USAGE_DATA

class SendMessage(BaseModel):
    messageId: str
    chargerId: str
    data: dict

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JSON_FILE = 'ocpp16/shared_data.json'

data_manager = JsonConfigManager(JSON_FILE)
connected_clients = {}  # client_id → websocket
pending_responses = {}  # client_id → asyncio.Future

# --- 🔌 OCPP 서버 설정 ---
OCPP_HOST = '127.0.0.1'
OCPP_PORT = 443
# CERT_FILE = 'certificate/cert.pem' 
# KEY_FILE = 'certificate/key.pem'
CERT_FILE = 'certificate/open-ocpp_central-system.crt' 
KEY_FILE = 'certificate/open-ocpp_central-system.key'
HB_INTERVAL = 180 # Heartbeat 주기 (초)


# --- 🔌 OCPP 연결 관리 함수 ---

async def ocpp_connection_handler(websocket, path):
    """새로운 웹소켓 연결을 처리하고, 메시지를 ocpp_message.py로 라우팅합니다."""
    try:
        # if not path.startswith('/openocpp/'):
        if not path.startswith('/'):
            return await websocket.close()
            
        charger_id = path.split('/')[-1]
        if not charger_id:
            return await websocket.close()
            
    except Exception:
        return await websocket.close()

    print(f"\n[{charger_id}] [info] 새 충전기 연결 시도: {websocket.remote_address}")
    connected_clients[charger_id] = websocket

    try:
        # 메시지 라우팅을 외부 모듈(ocpp_message.py)의 함수로 전달
        async for message in websocket:
            try:
                await route_ocpp_message(charger_id, message, websocket, SHARED_DATA, HB_INTERVAL)
            except Exception as e:
                print(f"[{charger_id}] [error] 메시지 처리 중 오류 발생 in ocpp_connection_handler(): {e}")
            
    except websocket.exceptions.ConnectionClosedOK:
        print(f"[{charger_id}] [info] 연결 정상 종료")
    except websocket.exceptions.ConnectionClosedError as e:
        print(f"[{charger_id}] [info] 연결 오류 종료: {e}")
    except Exception as e:
        print(f"[{charger_id}] [error] 연결 루프 중 예상치 못한 오류 발생: {e}")
        
    finally:
        if charger_id in connected_clients:
            del connected_clients[charger_id]
        print(f"[{charger_id}] [info] 연결 해제. 현재 연결 수: {len(connected_clients)}")

# @app.websocket("/openocpp/{charger_id}")
@app.websocket("/{charger_id}")
async def ws_endpoint(websocket: WebSocket, charger_id: str):
    await websocket.accept()

    # if charger_id in SHARED_DATA['registered_chargers']:
    SHARED_DATA = data_manager.load_data()
    if charger_id in SHARED_DATA['registered_chargers']:
        connected_clients[charger_id] = websocket
        print(f"Client {charger_id} connected")
    else:
        print(f"Client {charger_id} not registered. Closing connection.")
        await websocket.close()
        return

    try:
        while True:
            message = await websocket.receive_text() 
            try:
                await route_ocpp_message(charger_id, message, websocket, SHARED_DATA, HB_INTERVAL)
            except json.JSONDecodeError:
                print(f"[{charger_id}] [error] JSON 디코딩 오류: 수신된 메시지가 유효한 JSON이 아닙니다.")
            except Exception as e:
                print(f"[{charger_id}] [error] 메시지 처리 중 예외 발생: {e}")

    except Exception as e:
        print(f"Client {charger_id} error: {e}")
    finally:
        connected_clients.pop(charger_id, None)

@app.post("/send")
async def send_to_client(request_body: SendMessage):
    message_id = request_body.messageId
    payload = request_body.data
    charger_id = request_body.chargerId
    print(f"[HTTP] /send 엔드포인트 호출 - charger_id: {charger_id}, messageId: {message_id}, payload: {payload}")

    timeout_seconds = 30.0

    if message_id == "uvCardRegister":
        if charger_id not in connected_clients:
            return {"error": "Client not connected"}
        # 응답을 기다릴 Future 생성
        if charger_id not in pending_responses:
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            pending_responses[charger_id] = future
            print(f"[HTTP] 충전기 '{charger_id}'의 다음 Authorize idTag를 {timeout_seconds}초 동안 대기합니다.")

        try:
            # 클라이언트의 응답을 대기
            response = await asyncio.wait_for(future, timeout=timeout_seconds)
            cardnumber = response.get('idTag')
        except asyncio.TimeoutError:
            response = "timeout"
            cardnumber = None
        finally:
            pending_responses.pop(charger_id, None)
        print(f"info: send_to_client 함수가 응답을 받았습니다. charger_id: {charger_id}, idTag: {response} ")
        return {'cardnumber': cardnumber}
    elif message_id == "scheduledCharging":
        print(f"[HTTP] scheduledCharging 메시지 처리 중 - charger_id: {charger_id} payload: {payload}")
    elif message_id == "energyUsage":
        energy_usage_data = payload
        print(f"[HTTP] Energy usage 메시지 처리 중 - charger_id: {charger_id} payload: {energy_usage_data}")

async def handle_boot_notification(charger_id: str, unique_id: str, payload: dict, SHARED_DATA: dict, hb_interval: int) -> str:
    # 1. 관리 시스템(Flask)에 등록된 충전기인지 확인
    if charger_id not in SHARED_DATA['registered_chargers']:
        print(f"[{charger_id}] BootNotification Rejected: 관리 시스템에 미등록된 ID")
        error_response = [4, unique_id, "SecurityError", "Charger ID not registered", {}]
        return json.dumps(error_response)
        
    # 2. 서버 로직 처리 및 응답 생성
    vendor = payload.get('chargePointVendor')
    model = payload.get('chargePointModel')

    if SHARED_DATA['registered_chargers'][charger_id]['chargePointVendor'] != vendor or SHARED_DATA['registered_chargers'][charger_id]['chargePointModel'] != model:
        print(f"[{charger_id}] BootNotification Rejected: Charger details are not identical")
        error_response = [4, unique_id, "SecurityError", "Charger details are not identical", {}]
        return json.dumps(error_response)
    
    response_payload = {
        "status": "Accepted",
        "currentTime": datetime.now(timezone.utc).isoformat() + "Z",
        "interval": hb_interval
    }
    return json.dumps([3, unique_id, response_payload])

async def handle_authorize(charger_id: str, unique_id: str, payload: dict, SHARED_DATA: dict) -> str:
    """
    Authorize 요청을 처리하고 응답을 생성합니다.
    관리 시스템(SHARED_DATA)에 등록된 ID Tag인지 확인합니다.
    """
    if charger_id in pending_responses:
        await set_future_result(charger_id, payload)

    id_tag = payload.get('idTag')
    SHARED_DATA = data_manager.load_data()
    
    if id_tag in SHARED_DATA['registered_id_tags']:
        tag_info = {
            'status': SHARED_DATA['registered_id_tags'][id_tag]['status'],
            'expiryDate': SHARED_DATA['registered_id_tags'][id_tag]['expiryDate']
        }   
    else:
        tag_info = {
            'status': 'Invalid',
            'expiryDate': None
        }

    response_payload = {
        "idTagInfo": tag_info
    }
    return json.dumps([3, unique_id, response_payload])

async def route_ocpp_message(charger_id: str, message: str, websocket, shared_data: dict, hb_interval: int):
    """수신된 OCPP 메시지를 라우팅하고 처리합니다."""
    try:
        data = json.loads(message)
        if data[0] == 2 and len(data) == 4:
            print(f"[{charger_id}] [recv] Request for {data[2]} (ID: {data[1]}): {data[3]}")
        elif data[0] == 3 and len(data) == 3:
            print(f"[{charger_id}] [recv] Response for (ID: {data[1]}): {data[2]}")
        else:
            print(f"[{charger_id}] [recv] Unknown message format: {data}")

        # Call 메시지 형식 확인: [2, <UniqueID>, "<Action>", {<Payload>}]
        if data[0] == 2 and len(data) == 4:
            unique_id = data[1]
            action = data[2]
            payload = data[3]
            
            response_message = None
            
            # Action에 따른 처리 로직 분기
            if action == "BootNotification":
                # SHARED_DATA와 HB_INTERVAL 인자를 전달
                response_message = await handle_boot_notification(charger_id, unique_id, payload, shared_data, hb_interval)
            elif action == "Authorize":
                # SHARED_DATA 인자를 전달
                response_message = await handle_authorize(charger_id, unique_id, payload, shared_data)
            elif action == "Heartbeat":
                # Heartbeat 처리 로직 datetime.now(timezone.utc).isoformat() + "Z"
                response_message = json.dumps([3, unique_id, {"currentTime": datetime.now(timezone.utc).isoformat() + "Z"}])
            elif action == "DataTransfer":
                # 여기서는 충전기가 서버로 보낸 DataTransfer 요청에 대한 응답을 처리합니다.
                # 예시: 서버는 단순히 'Accepted'를 응답
                response_payload = {"status": "Accepted"}
                response_message = json.dumps([3, unique_id, response_payload])
            elif action == "StatusNotification":
                # 여기서는 충전기가 서버로 보낸 DataTransfer 요청에 대한 응답을 처리합니다.
                # 예시: 서버는 단순히 'Accepted'를 응답
                response_payload = {}
                response_message = json.dumps([3, unique_id, response_payload])
            else:
                # 지원하지 않는 Action
                error_response = [4, unique_id, "NotImplemented", "Action not supported", {}]
                response_message = json.dumps(error_response)
            if response_message:
                try:
                    await websocket.send_text(response_message)
                    print(f"[{charger_id}] [send] Response for {action} (ID: {unique_id}): {response_message}")
                except Exception as e:
                    print(f"[{charger_id}] [error] 응답 전송 실패: {e}")
        # CallResult 메시지 형식 확인: [3, <UniqueID>, {<Payload>}]
        elif data[0] == 3 and len(data) == 3:
            # 서버가 충전기에 보낸 요청(예: DataTransfer)에 대한 응답 처리
            unique_id = data[1]
            response_payload = data[2]

            # await set_future_result(unique_id, response_payload)

    except Exception as e:
        print(f"[{charger_id}] [error] 메시지 처리 중 오류 발생 in route_ocpp_message(): {e}")

async def set_future_result(unique_id: str, response_data: dict):
    future = pending_responses.pop(unique_id, None)

    if future:
        # 3. Future 객체의 결과 설정 (set_result)
        if not future.done():
            future.set_result(response_data)
            print(f" Future result set for ID: {unique_id}")
        else:
            # 이미 타임아웃 등에 의해 취소/완료된 경우 (발생 가능성은 낮음)
            print(f" Future for ID: {unique_id} was already done/cancelled.")
    else:
        # 해당 요청을 기다리는 Future가 없는 경우 (이미 타임아웃되거나 예상치 못한 응답)
        print(f" No pending request found for ID: {unique_id}. (May have timed out)")


def start_ocpp_server(app):
    # SSL Context를 직접 정의할 필요는 없습니다. Uvicorn에 파일 경로만 전달하면 됩니다.
    # 만약 OCPP 서버가 WSS 포트(예: 443)에서 실행되어야 한다면 포트를 변경합니다.
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=443, 
        ssl_keyfile=KEY_FILE,    # 💡 키 파일 경로
        ssl_certfile=CERT_FILE  # 💡 인증서 파일 경로
    )

if __name__ == "__main__":
    start_ocpp_server(app)