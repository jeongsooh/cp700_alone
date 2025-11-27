# models.py
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

class Fcuser(db.Model):
    __tablename__ = 'fcuser'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    username = db.Column(db.String(32), nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'userid': self.userid,
            'password': self.password,
            'username': self.username
        }

class Energy(db.Model):
    __tablename__ = 'energy'
    id = db.Column(db.Integer, primary_key=True)
    serialnumber = db.Column(db.String(32), unique=True, nullable=False)
    maxcurrent = db.Column(db.Integer, nullable=False)
    schedule_enabled = db.Column(db.Boolean, default=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'serialnumber': self.serialnumber,
            'maxcurrent': self.maxcurrent,
            'schedule_enabled': self.schedule_enabled
        }

class Card(db.Model):
    __tablename__ = 'card'
    id = db.Column(db.Integer, primary_key=True)
    cardname = db.Column(db.String(32), unique=True, nullable=False)
    cardnumber = db.Column(db.String(32), unique=True, nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'cardname': self.cardname,
            'cardnumber': self.cardnumber,
        }

class Scheduled(db.Model):
    __tablename__ = 'scheduled'
    id = db.Column(db.Integer, primary_key=True)
    timezone = db.Column(db.String(32), unique=True, nullable=False)
    starttime = db.Column(db.String(32), nullable=False)
    endtime = db.Column(db.String(32), nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'timezone': self.timezone,
            'starttime': self.starttime,
            'endtime': self.endtime,
        }