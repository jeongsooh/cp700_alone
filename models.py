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

class Charger(db.Model):
    __tablename__ = 'charger'
    id = db.Column(db.Integer, primary_key=True)
    charger_id = db.Column(db.String(32), unique=True, nullable=False)
    vendor = db.Column(db.String(32), nullable=False)
    connected = db.Column(db.Boolean, default=False, nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'charger_id': self.charger_id,
            'vendor': self.vendor,
            'connected': self.connected
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
    status = db.Column(db.String(32), unique=True, nullable=False)
    expirydate = db.Column(db.DateTime, nullable=False)

    @property
    def serialize(self):
        expirydate_str = self.expirydate.strftime('%Y-%m-%dT%H:%M:%S') if self.expirydate else None
        return {
            'id': self.id,
            'cardname': self.cardname,
            'cardnumber': self.cardnumber,
            'status': self.status,
            'expirydate': expirydate_str
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