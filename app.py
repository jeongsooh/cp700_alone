# app.py
import os
import asyncio
from flask import Flask, render_template, request, jsonify
from flask_jwt_extended import create_access_token
from flask_jwt_extended import JWTManager
from models import db, Fcuser
from api_v1 import api as api_v1
from api_v1.user import create_default_user

app = Flask(__name__)
app.register_blueprint(api_v1, url_prefix='/api/v1')
FLASK_PORT = 5000
OCPP_HOST = '0.0.0.0'
OCPP_PORT = 443

@app.route('/chpasswd')
def chpasswd():
    return render_template('chpasswd.html')

@app.route('/devregister')
def devregister():
    return render_template('devregister.html')

@app.route('/cardregister')
def cardregister():
    return render_template('cardregister.html')

@app.route('/cardregisteronline')
def cardregister_online():
    return render_template('cardregister_online.html')

@app.route('/setschedule')
def setschedule():
    return render_template('setschedule.html')

@app.route('/login', methods=['GET'])
# @jwt_required
def login():
    return render_template('login.html')

@app.route('/')
def hello():
    return render_template('home.html')


@app.route('/api/chargers', methods=['GET', 'POST'])
def manage_chargers():
    """등록된 충전기 목록 조회 및 신규 충전기 등록"""
    if request.method == 'GET':
        status_list = []
        for cid, info in SHARED_DATA['registered_chargers'].items():
            info['is_connected'] = cid in SHARED_DATA['connected_chargers']
            status_list.append({cid: info})
        return jsonify(status_list)

    if request.method == 'POST':
        data = request.json
        charger_id = data.get('charger_id')
        if not charger_id:
            return jsonify({"error": "Charger ID is required"}), 400
        
        SHARED_DATA['registered_chargers'][charger_id] = {
            "vendor": data.get("vendor", "N/A"),
            "model": data.get("model", "N/A")
        }
        return jsonify({"message": f"Charger {charger_id} registered successfully"}), 201

@app.route('/api/tags/<tag_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_id_tags(tag_id):
    if request.method == 'GET':
        tag_info = SHARED_DATA['registered_id_tags'].get(tag_id)
        if tag_info:
            return jsonify(tag_info)
        return jsonify({"error": "ID Tag not found"}), 404

    if request.method == 'PUT':
        data = request.json
        SHARED_DATA['registered_id_tags'][tag_id] = {
            "status": data.get("status", "Accepted"),
            "expiryDate": data.get("expiryDate", None)
        }
        return jsonify({"message": f"ID Tag {tag_id} updated"}), 200

    if request.method == 'DELETE':
        if tag_id in SHARED_DATA['registered_id_tags']:
            del SHARED_DATA['registered_id_tags'][tag_id]
            return jsonify({"message": f"ID Tag {tag_id} deleted"}), 200
        return jsonify({"error": "ID Tag not found"}), 404


basedir = os.path.abspath(os.path.dirname(__file__))
dbfile = os.path.join(basedir, 'db.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{dbfile}'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_test_here'

db.init_app(app)
db.app = app
app.app_context().push()
db.create_all()
create_default_user()

app.config['JWT_SECRET_KEY'] = 'your-secret-key'
jwt = JWTManager(app)

@app.route('/auth', methods=['POST'])
def auth():
    data = request.get_json()
    userid = data.get('userid')
    password = data.get('password')

    user = Fcuser.query.filter(Fcuser.userid == userid).first()
    if user and user.password == password:
        token = create_access_token(identity=userid)
        return jsonify(access_token=token)
    else:
        return jsonify(msg='Invalid credentials'), 401

if __name__ == '__main__':
    
    try:
        # asyncio.run(start_flask_app())
        app.run(host=OCPP_HOST, port=FLASK_PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n서버 통합 종료 요청...")