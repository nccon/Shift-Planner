from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    shifts = db.relationship('Shift', backref='user', lazy=True)
    requests = db.relationship('ShiftChangeRequest', backref='requesting_user', lazy=True, foreign_keys='ShiftChangeRequest.requester_id', overlaps="user_requests")
    target_requests = db.relationship('ShiftChangeRequest', backref='targeted_user', lazy=True, foreign_keys='ShiftChangeRequest.target_user_id', overlaps="user_target_requests")

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'phone': self.phone,
            'email': self.email,
            'is_admin': self.is_admin
        }

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    shift_type = db.Column(db.String(20), nullable=False)

    def __init__(self, user_id, start_date, end_date, shift_type):
        self.user_id = user_id
        self.start_date = start_date
        self.end_date = end_date
        self.shift_type = shift_type

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'shift_type': self.shift_type,
            'user': self.user.to_dict()
        }

class ShiftChangeRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')
    shift = db.relationship('Shift', backref='change_requests', lazy=True)
    requesting_user_rel = db.relationship('User', foreign_keys=[requester_id], overlaps="requesting_user")
    targeted_user_rel = db.relationship('User', foreign_keys=[target_user_id], overlaps="targeted_user")

    def to_dict(self):
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'requester_id': self.requester_id,
            'target_user_id': self.target_user_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status
        }
        
class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)    
    
class BankHoliday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    endpoint = db.Column(db.String(100), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'method': self.method,
            'endpoint': self.endpoint,
            'status_code': self.status_code,
            'duration': self.duration,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
