from flask import Blueprint

user_routes_bp = Blueprint('user_routes', __name__)

from .user import *