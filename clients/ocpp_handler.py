def ocpp_call_handler(message_id, action, payload):
    """OCPP CALL 메시지 핸들러"""
    if action == "Heartbeat":
        # Scenario 2.b: Heartbeat 요청 처리
        response_payload = {
            "currentTime": time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        }
        response_message = create_call_result(message_id, response_payload)
        return response_message
    elif action == "BootNotification":
        # Scenario 2.c: BootNotification 요청 처리
        response_payload = {
            "currentTime": time.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            "interval": HEARTBEAT_INTERVAL,
            "status": "Accepted"
        }
        response_message = create_call_result(message_id, response_payload)
        return response_message
    else:
        print(f"Unhandled OCPP action: {action}")
        return None
    
def ocpp_call_result_handler(message_id, action, payload):
    """OCPP CALL RESULT 메시지 핸들러"""
    # Confirmation from BootNotification
    if message_id == boot_message_id:
        HEARTBEAT_INTERVAL = payload.get('interval', DEFAULT_INTERVAL)
        print(f"<- Confirmation received. Heartbeat Interval set to {HEARTBEAT_INTERVAL}s.")
    elif action == "Authorize":
        # Scenario 2.d: Authorize 응답 처리
        id_tag_info = payload.get("idTagInfo", {})
        status = id_tag_info.get("status", "Unknown")
        print(f"Authorize Response: ID Tag Status = {status}")
    elif action == "StatusNotification":
        # Scenario 2.e: StatusNotification 응답 처리
        print("StatusNotification confirmed by server.")
    else:
        print(f"Unhandled OCPP CALL RESULT action: {action}")
