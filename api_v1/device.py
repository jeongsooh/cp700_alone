# api_v1/device.py
import requests
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
        if Energy.query.all():
            return jsonify({"error": "One device is allowed and already exists."}), 201
        device = Energy()
        device.serialnumber = serialnumber
        device.maxcurrent = maxcurrent

        db.session.add(device)
        db.session.commit()
        # Optionally, connect to WiFi after adding the device
        # connect_wifi(serialnumber)

        return jsonify({"message": "Device added successfully."}), 201
    devices = Energy.query.all()
    return jsonify([device.serialize for device in devices])
           
@api.route('/devices/<uid>', methods=['GET', 'PUT', 'DELETE'])
def device_detail(uid):
    if request.method == 'GET':
        device = Energy.query.filter(Energy.id == uid).first()
        if device:
            return jsonify(device.serialize)
        else:
            return jsonify({"error": "Device not found."}), 404
    elif request.method == 'DELETE':
        device = Energy.query.filter(Energy.id == uid).first()
        if device:
            db.session.delete(device)
            db.session.commit()
            return jsonify({"message": "Device deleted successfully."}), 200
        else:
            return jsonify({"error": "Device not found."}), 404
    elif request.method == 'PUT':
        device = Energy.query.filter(Energy.id == uid).first()
        device.schedule_enabled = not device.schedule_enabled
        Energy.query.filter(Energy.id == uid).update({"schedule_enabled": device.schedule_enabled})
        print(f"Device {uid} schedule_enabled toggled to {device.schedule_enabled}")
        db.session.commit()
        return jsonify({"message": "Schedule enabled status toggled successfully."}), 200

    data = request.get_json()

    Energy.query.filter(Energy.id == uid).update(data)
    db.session.commit()
    device = Energy.query.filter(Energy.id == uid).first()
    return jsonify(device.serialize)
           
@api.route('/cards/<uid>', methods=['GET', 'PUT', 'DELETE'])
def card_detail(uid):
    if request.method == 'GET':
        card = Card.query.filter(Card.id == uid).first()
        if card:
            return jsonify(card.serialize)
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
        payload = {"messageId": "uvCardRegister", "charger_id": charger_id}

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
        timezone = data.get('timezone')
        starttime = data.get('starttime')
        endtime = data.get('endtime')

        if not (timezone and starttime and endtime):
            return jsonify({"error": "All fields are required."}), 400
        schedule = Scheduled()
        schedule.timezone = timezone
        schedule.starttime = starttime
        schedule.endtime = endtime

        db.session.add(schedule)
        db.session.commit()
        return jsonify({"message": "Charging schedule is set successfully."}), 201
    schedules = Scheduled.query.all()
    return jsonify([schedule.serialize for schedule in schedules])
           
@api.route('/scheduled/<uid>', methods=['GET', 'PUT', 'DELETE'])
def schedule_detail(uid):
    if request.method == 'GET':
        schedule = Scheduled.query.filter(Scheduled.id == uid).first()
        if schedule:
            return jsonify(schedule.serialize)
        else:
            return jsonify({"error": "Schedule not found."}), 404
    elif request.method == 'DELETE':
        schedule = Scheduled.query.filter(Scheduled.id == uid).first()
        if schedule:
            db.session.delete(schedule)
            db.session.commit()
            return jsonify({"message": "Schedule deleted successfully."}), 200
        else:
            return jsonify({"error": "Schedule not found."}), 404
    
    data = request.get_json()

    Scheduled.query.filter(Scheduled.id == uid).update(data)
    db.session.commit()
    schedule = Scheduled.query.filter(Scheduled.id == uid).first()
    return jsonify(schedule.serialize)