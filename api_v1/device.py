# api_v1/device.py
import requests
import json
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Fcuser, db, Energy, Card, Scheduled
from . import api
from ocpp16.data_manager import JsonConfigManager
from datetime import datetime, timezone, timedelta

SERVER_URL = "https://127.0.0.1:443/send"   # FastAPI 서버 주소
CERT_FILE = 'certificate/cert.pem' 
JSON_FILE = 'ocpp16/shared_data.json'

manager = JsonConfigManager(JSON_FILE)

@api.route('/devices', methods=['GET', 'POST'])
def devices():
    if request.method == 'POST':
        data = request.get_json()
        serialnumber = data.get('serialnumber')
        maxcurrent = data.get('maxcurrent')

        if not (serialnumber and maxcurrent):
            return jsonify({"error": "All fields are required."}), 201
        
        # Check if a device already exists
        devices = manager.load_data()
        print(devices.get('pm_devices'))
        if devices.get('pm_devices'):
            return jsonify({"error": "One device is allowed and already exists."}), 201
        if serialnumber in devices.get('pm_devices', {}).items():
            return jsonify({"error": "The device already exists."}), 201
        
        manager.update_pm_device(
            serialnumber=serialnumber, 
            maxcurrent=maxcurrent 
        )
        return jsonify({"message": "PM device added successfully."}), 201
    
    devices = manager.load_data()
    count = 0
    response = []
    for serialnumber, maxcurrent in devices.get('pm_devices', {}).items():
        device = {'id': count, 'serialnumber': serialnumber, 'maxcurrent': maxcurrent}
        response.append(device)
        count += 1
    return jsonify(response)
           
@api.route('/devices/<uid>', methods=['GET', 'PUT', 'DELETE'])
def device_detail(uid):
    if request.method == 'GET':
        device = manager.get_nth_pm_device(int(uid))
        if device:
            response = []
            data = manager.load_data()
            devices = data.get('pm_devices', {})
            device = {'id': uid, 'serialnumber': device, 'maxcurrent': devices[device]}
            response.append(device)
            return jsonify(response)
        else:
            return jsonify({"error": "Device not found."}), 404
    elif request.method == 'DELETE':
        device = manager.get_nth_pm_device(int(uid))
        if device:
            manager.delete_pm_device(device)
            return jsonify({"message": "Device deleted successfully."}), 200
        else:
            return jsonify({"error": "Device not found."}), 404

    devices = manager.load_data()
    count = 0
    response = []
    for serialnumber, maxcurrent in devices.get('pm_devices', {}).items():
        device = {'id': count, 'serialnumber': serialnumber, 'maxcurrent': maxcurrent}
        response.append(device)
        count += 1
    return jsonify(response)
           
@api.route('/cards/<uid>', methods=['GET', 'PUT', 'DELETE'])
def card_detail(uid):
    if request.method == 'GET':
        device = manager.get_nth_pm_device(int(uid))
        if device:
            response = []
            data = manager.load_data()
            devices = data.get('pm_devices', {})
            device = {'id': uid, 'serialnumber': device, 'maxcurrent': devices[device]}
            response.append(device)
            return jsonify(response)
        else:
            return jsonify({"error": "Card not found."}), 404
    elif request.method == 'DELETE':
        card = manager.get_nth_id_tag(int(uid))
        if card:
            manager.delete_id_tag(card)
            return jsonify({"message": "Card deleted successfully."}), 200
        else:
            return jsonify({"error": "Card not found."}), 404
    
    cards = manager.load_data()
    count = 0
    response = []
    for id_tag, info in cards.get('registered_id_tags', {}).items():
        card = {'id': count, 'cardname': info.get('cardname', ''), 'cardnumber': id_tag, 'status': info.get('status', ''), 'expirydate': info.get('expiryDate', '')}
        response.append(card)
        count += 1
    return jsonify(response)

@api.route('/cards', methods=['GET', 'POST'])
def cards():
    if request.method == 'POST':
        data = request.get_json()
        cardname = data.get('cardname')
        cardnumber = data.get('cardnumber')
        status = data.get('status')
        expirydate = datetime.now(timezone.utc) + timedelta(days=365)  # 예시: 1년 후 만료

        if not (cardname and cardnumber):
            return jsonify({"error": "All fields are required."}), 400

        manager.update_id_tag(
            id_tag=cardnumber, 
            status=status, 
            cardname=cardname, 
            expiry_days=365 # 1년 후 만료
        )
        return jsonify({"message": "Card added successfully."}), 201

    cards = manager.load_data()
    count = 0
    response = []
    for id_tag, info in cards.get('registered_id_tags', {}).items():
        card = {'id': count, 'cardname': info.get('cardname', ''), 'cardnumber': id_tag, 'status': info.get('status', ''), 'expirydate': info.get('expiryDate', '')}
        response.append(card)
        count += 1
    return jsonify(response)

@api.route('/registeronline', methods=['GET', 'POST'])
def cards_online():
    if request.method == 'POST':
        data = request.get_json()
        cardname = data.get('cardname')
        charger_id = data.get('charger_id')

        if not charger_id or not cardname:
            return jsonify({"error": "Charger ID and Card name are both required."}), 400
        
        # 서버에 메시지 전달
        payload = {"messageId": "uvCardRegister", "chargerId": charger_id, "data": {"cardname": cardname}}

        res = requests.post(SERVER_URL, 
            json=payload,
            # verify=CERT_FILE
            verify=False
        )

        print(f"Response from server: {res.json()}")

        if res.status_code != 200:
            print(f"error: Failed to send command, status: {res.status_code}")
            return jsonify({"error": "Failed to communicate with FastAPI server.", "details": res.text}), 502

        cardnumber = res.json().get('cardnumber')
        if cardnumber is None:
            print("error: Card number is not retrieved.")
            return
        
        manager.update_id_tag(
            id_tag=cardnumber, 
            status="Accepted", 
            cardname=cardname, 
            expiry_days=365 # 1년 후 만료
        )
        return jsonify({"message": "Card added successfully."}), 201
    cards = manager.load_data()
    count = 0
    response = []
    for id_tag, info in cards.get('registered_id_tags', {}).items():
        card = {'id': count, 'cardname': info.get('cardname', ''), 'cardnumber': id_tag, 'status': info.get('status', ''), 'expirydate': info.get('expiryDate', '')}
        response.append(card)
        count += 1
    return jsonify(response)

@api.route('/scheduled', methods=['GET', 'POST'])
def scheduled():
    if request.method == 'POST':
        data = request.get_json()
        priority = data.get('priority')
        timezone = data.get('timezone')
        starttime = data.get('starttime')
        endtime = data.get('endtime')

        if not (timezone and starttime and endtime):
            return jsonify({"error": "All fields are required."}), 400
        
        manager.update_schedules(
            priority=priority,
            timezone=timezone, 
            starttime=starttime, 
            endtime=endtime 
        )
        return jsonify({"message": "Schedule added successfully."}), 201
    data = manager.load_data()
    schedule_enabled = data.get('scheduled_charging', False)    
    count = 0
    response = []
    for desc, info in data.get('schedules', {}).items():
        schedule = {'id': count, 'schedule_enabled': schedule_enabled, 'priority': desc, 'timezone': info.get('timezone', ''), 'starttime': info.get('starttime', ''), 'endtime': info.get('endtime', '')}
        response.append(schedule)
        count += 1
    return jsonify(response)
           
@api.route('/scheduled/<uid>', methods=['GET', 'PUT', 'DELETE'])
def schedule_detail(uid):
    if request.method == 'GET':
        pass
    elif request.method == 'DELETE':
        schedule = manager.get_nth_schedule(int(uid))
        if schedule:
            manager.delete_schedule(schedule)
            return jsonify({"message": "Schedule deleted successfully."}), 200
        else:
            return jsonify({"error": "Schedule not found."}), 404

    elif request.method == 'PUT':
        data = manager.load_data()
        schedules = data.get('schedules', {})
        if schedules is None:
            print("[Schedules] No schedules found to toggle.")
            return jsonify({"message": "No schedules found to toggle."}), 200
        else:
            data['scheduled_charging'] = not data['scheduled_charging']
            print(f"Schedule Charging toggled to {data['scheduled_charging']}")

        # 서버에 메시지 전달
        if schedules['priority'] is not None:
            priority = 'priority'
        else:
            priority = 'default'

        timezone = schedules[priority].get('timezone', '')
        starttime = schedules[priority].get('starttime', '')
        endtime = schedules[priority].get('endtime', '')

        payload = {
            "messageId": "scheduledCharging", 
            "chargerId": uid,
            "data": {
                "timezone": timezone,
                "starttime": starttime,
                "endtime": endtime
            }
        }
        res = requests.post(SERVER_URL, 
            json=payload,
            # verify=CERT_FILE
            verify=False
        )
        print(f"Response from server: {res.json()}")
        if res.status_code != 200:
            print(f"error: Failed to send command, status: {res.status_code}")
            return jsonify({"error": "Failed to communicate with FastAPI server.", "details": res.text}), 502

        manager.save_data(data)
        return jsonify({"message": "Scheduled Charging enable/disable status toggled successfully."}), 200
    
    data = manager.load_data()
    schedule_enabled = data.get('scheduled_charging', False)    
    count = 0
    response = []
    for desc, info in data.get('schedules', {}).items():
        schedule = {'id': count, 'schedule_enabled': schedule_enabled, 'priority': desc, 'timezone': info.get('timezone', ''), 'starttime': info.get('starttime', ''), 'endtime': info.get('endtime', '')}
        response.append(schedule)
        count += 1
    return jsonify(response)