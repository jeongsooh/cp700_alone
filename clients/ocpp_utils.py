# ocpp_utils.py
import json
import uuid

# OCPP 1.6 Message Type IDs
CALL = 2
CALL_RESULT = 3
CALL_ERROR = 4

def create_call(action, payload):
    """OCPP CALL (요청) 메시지를 생성합니다."""
    message_id = str(uuid.uuid4())
    message = [
        CALL,
        message_id,
        action,
        payload
    ]
    return json.dumps(message), message_id

def create_call_result(message_id, payload):
    """OCPP CALL RESULT (응답) 메시지를 생성합니다."""
    message = [
        CALL_RESULT,
        message_id,
        payload
    ]
    return json.dumps(message)

def parse_ocpp_message(raw_message):
    """수신된 JSON 메시지를 파싱합니다."""
    try:
        data = json.loads(raw_message)
        message_type_id = data[0]
        message_id = data[1]
        
        if message_type_id == CALL:
            action = data[2]
            payload = data[3]
            return message_type_id, message_id, action, payload
        elif message_type_id == CALL_RESULT:
            payload = data[2]
            return message_type_id, message_id, None, payload
        # ... CALL_ERROR 처리 생략
        return None
    except Exception as e:
        print(f"Error parsing message: {e}")
        return None