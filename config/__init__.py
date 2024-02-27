from flask import Flask
from config.db import init_db, mongo

def create_app():
    app = Flask(__name__)

    init_db(app)
    return app
