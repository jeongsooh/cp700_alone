# ocpp_message.py
import asyncio
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from shared_data import SHARED_DATA

class SendMessage(BaseModel):
    messageId: str
    charger_id: str

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients = {}  # client_id → websocket
pending_responses = {}  # client_id → asyncio.Future

# --- 🔌 OCPP 서버 설정 ---
OCPP_HOST = '127.0.0.1'
OCPP_PORT = 443
CERT_FILE = 'certificate/cert.pem' 
KEY_FILE = 'certificate/key.pem'
HB_INTERVAL = 180 # Heartbeat 주기 (초)


# --- 🔌 OCPP 연결 관리 함수 ---

async def ocpp_connection_handler(websocket, path):
    """새로운 웹소켓 연결을 처리하고, 메시지를 ocpp_message.py로 라우팅합니다."""
    try:
        if not path.startswith('/openocpp/'):
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

@app.websocket("/openocpp/{charger_id}")
async def ws_endpoint(websocket: WebSocket, charger_id: str):
    await websocket.accept()
    connected_clients[charger_id] = websocket
    print(f"Client {charger_id} connected")

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
    charger_id = request_body.charger_id
    messageId = request_body.messageId

    payload_data = {"memberId": "admin", "targetcp": charger_id}
    payload = {"messageId": messageId, "charger_id": charger_id}
    unique_id = str(uuid.uuid4())

    data_transfer_call = [
        2, # Call
        unique_id,
        "DataTransfer",
        {
            "vendorId": "gresystem",
            "messageId": messageId,
            "data": json.dumps(payload_data) # OCPP DataTransfer 스펙에 따라 'data'는 문자열(JSON String)이어야 합니다.
        }
    ]

    message_to_send = json.dumps(data_transfer_call)

    if charger_id not in connected_clients:
        return {"error": "Client not connected"}

    websocket = connected_clients[charger_id]
    # 응답을 기다릴 Future 생성
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    pending_responses[unique_id] = future

    # 메시지 전송
    await websocket.send_text(message_to_send)
    print(f"[{charger_id}] [send] Request for {message_to_send}")

    try:
        # 클라이언트의 응답을 대기
        response = await asyncio.wait_for(future, timeout=60)
        cardnumber = response.get('data')
    except asyncio.TimeoutError:
        response = "timeout"
    finally:
        pending_responses.pop(unique_id, None)
    print(f"info: send_to_client 함수가 응답을 받았습니다. charger_id: {charger_id}, response: {response} ")
    return {'cardnumber': cardnumber}

async def handle_boot_notification(charger_id: str, unique_id: str, payload: dict, shared_data: dict, hb_interval: int) -> str:
    # 1. 관리 시스템(Flask)에 등록된 충전기인지 확인
    if charger_id not in shared_data['registered_chargers']:
        print(f"[{charger_id}] BootNotification Rejected: 관리 시스템에 미등록된 ID")
        error_response = [4, unique_id, "SecurityError", "Charger ID not registered", {}]
        return json.dumps(error_response)
        
    # 2. 서버 로직 처리 및 응답 생성
    vendor = payload.get('chargePointVendor')
    model = payload.get('chargePointModel')
    
    response_payload = {
        "status": "Accepted",
        "currentTime": datetime.utcnow().isoformat() + "Z",
        "interval": hb_interval
    }
    
    return json.dumps([3, unique_id, response_payload])

async def handle_authorize(charger_id: str, unique_id: str, payload: dict, shared_data: dict) -> str:
    """
    Authorize 요청을 처리하고 응답을 생성합니다.
    관리 시스템(SHARED_DATA)에 등록된 ID Tag인지 확인합니다.
    """
    id_tag = payload.get('idTag')
    tag_info = shared_data['registered_id_tags'].get(id_tag)
    
    if tag_info and tag_info['status'] == 'Accepted':
        status = 'Accepted'
        print(f"[{charger_id}] 🔑 Authorize 승인: ID Tag {id_tag}")
    else:
        status = 'Invalid'
        print(f"[{charger_id}] 🔑 Authorize 거부: ID Tag {id_tag}")

    response_payload = {
        "idTagInfo": {
            "status": status,
            "expiryDate": tag_info.get('expiryDate') if tag_info else None
        }
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
                # Heartbeat 처리 로직
                response_message = json.dumps([3, unique_id, {"currentTime": datetime.utcnow().isoformat() + "Z"}])
            elif action == "DataTransfer":
                # 여기서는 충전기가 서버로 보낸 DataTransfer 요청에 대한 응답을 처리합니다.
                # 예시: 서버는 단순히 'Accepted'를 응답
                response_payload = {"status": "Accepted"}
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

            await set_future_result(unique_id, response_payload)

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