# client.py 
import asyncio
import websockets
import time
import sys
import json
import ssl
from ocpp_utils import CALL, CALL_RESULT, create_call, create_call_result, parse_ocpp_message

CHARGER_ID = sys.argv[1] if len(sys.argv) > 1 else "CHG-TEST-002"
WEBSOCKET_URL = f"wss://localhost:443/openocpp/{CHARGER_ID}"

# Global state
HEARTBEAT_INTERVAL = 180
DEFAULT_INTERVAL = 180
CHARGING_STATE = 'A' # A, B, C (Scenario 2.e)

CERT_FILE = '../certificate/cert.pem' 

async def send_status_notification(websocket, status, error_code="NoError"):
    """Scenario 2.e: 상태 변경 시 StatusNotification 전송"""
    payload = {
        "connectorId": 1,
        "errorCode": error_code,
        "status": status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    }
    message, message_id = create_call("StatusNotification", payload)
    await websocket.send(message)
    print(f"Sent StatusNotification ({status}). Waiting for Confirmation.")
    return message_id

async def send_authorize(websocket, id_tag):
    """Scenario 2.d: 사용자 인증 요청"""
    payload = {"idTag": id_tag}
    message, message_id = create_call("Authorize", payload)
    await websocket.send(message)
    print(f"Sent Authorize ({id_tag}). Waiting for Confirmation.")
    return message_id

async def heartbeat_loop(websocket):
    """Scenario 2.c: Heartbeat 인터벌 루프"""
    global HEARTBEAT_INTERVAL
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        payload = {"currentTime": time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"}
        message, _ = create_call("Heartbeat", payload)
        await websocket.send(message)
        print(f"-> Message sent: {message}")

async def handle_user_input(websocket):
    """Scenario 2.d & 2.e: 사용자 입력 처리 (인증, 상태 변경)"""
    global CHARGING_STATE
    while True:
        print("\n--- Input (C: Change State, A: Authorize) ---")
        user_input = await asyncio.to_thread(input, "Enter command (C/A): ")
        
        if user_input.upper() == 'C':
            # Scenario 2.e: Change State
            new_state = await asyncio.to_thread(input, f"Enter new state (A, B, C). Current: {CHARGING_STATE}: ")
            if new_state.upper() in ['A', 'B', 'C']:
                CHARGING_STATE = new_state.upper()
                await send_status_notification(websocket, "Charging")
            else:
                print("Invalid state.")
                
        elif user_input.upper() == 'A':
            # Scenario 2.d: Authorize
            id_tag = await asyncio.to_thread(input, "Enter Card ID (e.g., 12345): ")
            await send_authorize(websocket, id_tag)
            
        else:
            print("Invalid command.")

async def ocpp_client():
    """OCPP 클라이언트 메인 로직"""
    global HEARTBEAT_INTERVAL

    # Initialize task variables to avoid UnboundLocalError
    heartbeat_task = None
    user_input_task = None

    # SSL Context 설정 (서버의 자체 서명 인증서를 신뢰하도록 설정)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    try:
        # 서버의 cert.pem 파일을 신뢰 목록에 추가
        ssl_context.load_verify_locations(CERT_FILE)
        print(f"✅ 서버 인증서({CERT_FILE})를 신뢰 목록에 추가했습니다.")
    except FileNotFoundError:
        # cert.pem이 없으면 TLS 검증을 비활성화 (보안상 위험, 테스트용)
        print("⚠️ cert.pem 파일을 찾을 수 없습니다. 인증서 검증을 비활성화하고 진행합니다.")
        ssl_context.verify_mode = ssl.CERT_NONE

    print(f"🔌 클라이언트 {CHARGER_ID}가 서버 {WEBSOCKET_URL}에 접속 시도...")

    try:
        # Note: Use WSS if server is running on WSS (port 433)
        async with websockets.connect(
            WEBSOCKET_URL, 
            subprotocols=['ocpp1.6'],
            ssl=ssl_context
        ) as websocket:
            print(f"Connected to {WEBSOCKET_URL}. Sending BootNotification...")
            
            # Scenario 2.c: BootNotification
            payload = {
                "chargePointVendor": "UV-Tech",
                "chargePointModel": "UV-1000"
            }
            boot_message, boot_message_id = create_call("BootNotification", payload)
            await websocket.send(boot_message)
            print(f"-> Message sent: {boot_message}")

            # Start the heartbeat loop immediately after sending BootNotification
            heartbeat_task = asyncio.create_task(heartbeat_loop(websocket))
            user_input_task = asyncio.create_task(handle_user_input(websocket))
            
            # Message listening loop
            async for message in websocket:
                result = parse_ocpp_message(message)
                if not result: 
                    continue
                else:
                    print(f"<- Message received: {message}")

                message_type_id, message_id, action, payload = result
                print(f"Parsed Message - Type: {message_type_id}, ID: {message_id}, Action: {action}, Payload: {payload}")
                
                if message_type_id == CALL_RESULT:
                    # Confirmation from BootNotification
                    if message_id == boot_message_id:
                        HEARTBEAT_INTERVAL = payload.get('interval', DEFAULT_INTERVAL)
                        print(f"<- Confirmation received. Heartbeat Interval set to {HEARTBEAT_INTERVAL}s.")
                        
                elif message_type_id == CALL:
                    # Handle requests from CSMS
                    if action == "DataTransfer":
                        messageId = payload.get('messageId')
                        message_data = payload.get('data')
                        charger_id = json.loads(message_data).get('targetcp') if message_data else None
                        print(f"DataTransfer payload with messageId: {messageId}, charger_id: {charger_id}")

                        if messageId == "uvCardRegister":
                            # Scenario 2.f: Handle uvCardRegister
                            # Simulate card tag reading
                            # card_tag = await asyncio.to_thread(input, "\n*** CARD REGISTRATION PENDING ***\nTag a card now (Enter Card Tag): ")
                            card_tag = "1010010188889999"
                            
                            # Send back the card tag using DataTransfer
                            response_payload = {
                                "vendorId": "UV-Tech",
                                "messageId": "uvCardRegisterTag",
                                "data": card_tag
                            }
                            res_to_send = create_call_result(message_id, response_payload)
                            print(f"-> Message sending.....: {res_to_send}")
                            # Send DataTransfer back to the server. The server expects a CALL_RESULT to the original DataTransfer.
                            # We send a DataTransfer *containing* the card tag, which the server will process, 
                            # and then the server will send a CALL_RESULT to our original DataTransfer (if it was a response to an original CALL).
                            # For simplicity, we just respond with the CALL_RESULT to the original "uvCardRegister" CALL.
                            await websocket.send(res_to_send)
                            print(f"Simulated card read: {card_tag}. Sent DataTransfer Confirmation.")
                            
                    elif action == "ChangeConfiguration":
                        key = payload.get('key')
                        value = payload.get('value')
                        
                        if key == "HeartbeatInterval":
                            HEARTBEAT_INTERVAL = int(value)
                            response_payload = {"status": "Accepted"}
                            await websocket.send(create_call_result(message_id, response_payload))
                            print(f"Heartbeat Interval changed by CSMS to {HEARTBEAT_INTERVAL}s.")
                            
    except websockets.exceptions.InvalidStatus as e:
        print(f"Connection failed due to invalid status: {e}. Check server status and subprotocols.")
    except OSError: # Catch the low-level OS error for refusal/timeout
        print(f"Connection refused to {WEBSOCKET_URL}. Is server.py running?")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Only attempt to cancel if the task was actually created (not None)
        if heartbeat_task:
            heartbeat_task.cancel()
        if user_input_task:
            user_input_task.cancel()
        print("[Client] Disconnected.")

if __name__ == '__main__':
    # Scenario 4: Test Environment/Execution
    print(f"Starting OCPP Client with Charger ID: {CHARGER_ID}")
    print("---------------------------------------")
    try:
        # async_loop = asyncio.get_event_loop()
        asyncio.run(ocpp_client())
        # async_loop.run_until_complete(start_ocpp_server())
    except KeyboardInterrupt:
        print("\n[Client] CTRL+C Detected. Shutting down...")
    finally:
        print("[Client] Goodbye.")