# api_v1/user.py
from flask import jsonify, request
from flask_jwt_extended import jwt_required
from models import Fcuser, db
from . import api

@api.route('/users', methods=['GET', 'POST'])
@jwt_required()
def users():
    if request.method == 'POST':
        data = request.get_json()
        password = data.get('password')
        new_password = data.get('new_password')
        re_password = data.get('re_password')

        user = Fcuser.query.filter(Fcuser.userid == "admin").first()
        if user.password != password:
            return jsonify({"error": "Current password is incorrect."}), 400
        if not (new_password and password and re_password):
            return jsonify({"error": "All fields are required."}), 400
        if new_password != re_password:
            return jsonify({"error": "New passwords do not match."}), 400
        
        user.password = new_password

        db.session.commit()

        return jsonify({"message": "Password changed successfully."}), 201
    users = Fcuser.query.all()
    return jsonify([user.serialize for user in users])
           
@api.route('/users/<uid>', methods=['GET', 'PUT', 'DELETE'])
def users_detail(uid):
    if request.method == 'GET':
        user = Fcuser.query.filter(Fcuser.id == uid).first()
        if user:
            return jsonify(user.serialize)
        else:
            return jsonify({"error": "User not found."}), 404
    elif request.method == 'DELETE':
        user = Fcuser.query.filter(Fcuser.id == uid).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            return jsonify({"message": "User deleted successfully."}), 200
        else:
            return jsonify({"error": "User not found."}), 404
    
    data = request.get_json()

    Fcuser.query.filter(Fcuser.id == uid).update(data)
    db.session.commit()
    # Fcuser.query.filter(Fcuser.id == uid).update(updated_data)
    user = Fcuser.query.filter(Fcuser.id == uid).first()
    return jsonify(user.serialize)
    # return jsonify({"message": "User updated successfully."}), 200 if user else jsonify({"error": "User not found."}), 404 

def create_default_user():
    default_user = Fcuser.query.filter(Fcuser.userid == 'admin').first()
    if not default_user:
        default_user = Fcuser(userid='admin', username='Administrator', password='admin123')
        db.session.add(default_user)
        db.session.commit()
        print("Default user created.")




