from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade, migrate, init
import sys
from config import Config
from models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    migrate = Migrate(app, db)
    return app

app = create_app()

def main():
    with app.app_context():
        if 'init' in sys.argv:
            init()
        if 'migrate' in sys.argv:
            message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "migration"
            migrate(message)
        if 'upgrade' in sys.argv:
            upgrade()

if __name__ == '__main__':
    main()
