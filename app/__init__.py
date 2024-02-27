# app/__init__.py
from flask import Flask
from config.db import mongo
import os
from flask_jwt_extended import JWTManager
from flasgger import Swagger, swag_from

def create_app():
    app = Flask(__name__)
    
    # Configuração do Swagger para usar o arquivo documentation.json
    app.config['SWAGGER'] = {
    'title': 'TR Latam API Documentation',
    'uiversion': 3,
    'openapi': '3.0.2',
    'version': '1.0',
    'specs_route': '/apidocs/',
    'swagger_ui': True,  # Habilita o Swagger UI
    'specs': [
        {
            'endpoint': 'documentation',
            'route': '/documentation.json',
            'rule_filter': lambda rule: True,  # Mostra todas as regras na documentação
            'model_filter': lambda tag: True,  # Mostra todos os modelos na documentação
        }
    ]
}
    Swagger(app)

    # Configuração do MongoDB
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
    mongo.init_app(app)

    # Configuração do Flask JWT Extended
    app.config['JWT_SECRET_KEY'] = '4hSN-iBJTODPf_OpNvi0J2kWEISBGkM1K3qsq6dKbiw'
    app.config['JWT_TOKEN_LOCATION'] = ['headers']

    # Inicialização do Flask JWT Extended
    jwt = JWTManager(app)

    # Registrar Blueprints
    from app.user_routes.user import user_routes_bp
    from app.company_routes.company import company_routes_bp

    app.register_blueprint(user_routes_bp)
    app.register_blueprint(company_routes_bp)

    return app