from app import db, app
from models import User, Shift, ShiftChangeRequest

with app.app_context():
	db.create_all()
