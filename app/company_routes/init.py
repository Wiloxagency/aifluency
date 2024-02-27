from flask import Blueprint

company_routes_bp = Blueprint('company_routes', __name__)

from .company import *