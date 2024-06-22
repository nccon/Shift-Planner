import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('your_random_key') or 'your_random_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///shiftPlanner_db.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    DEBUG = True
