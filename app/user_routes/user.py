from flask import Blueprint, jsonify, request
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo
import datetime
from bson import ObjectId
import jwt
from config.db import mongo
from flask_jwt_extended import jwt_required, get_jwt_identity
from jwt import InvalidTokenError
from bson import json_util
from flasgger import Swagger, swag_from

user_routes_bp = Blueprint('user_routes', __name__)
bcrypt = Bcrypt()

@user_routes_bp.route('/users', methods=['GET'])
@swag_from({
    'tags': ['user'],
    'responses': {
        200: {
            'description': 'List of all users',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'username': {'type': 'string'},
                        'email': {'type': 'string'},
                        # Add more properties as needed
                    }
                }
            }
        }
    }
})
def get_all_users():
    """
    Get the list of all users.

    This function returns a list of users, excluding the password.

    :return: List of users.
    """
    db = mongo.db
    collection = db['user']

    users = list(collection.find({}, {'password': 0}))

    for user in users:
        if "_id" in user:
            user["_id"] = str(user["_id"])

    return jsonify(users)

# Create User
@user_routes_bp.route('/users', methods=['POST'])
@swag_from({
    'operationId': 'create_user',
    'tags': ['user'],
    'parameters': [
        {
            'in': 'body',
            'name': 'user',
            'description': 'User data for creating a new user',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'example': 'john.doe@example.com'},
                    'password': {'type': 'string', 'example': 'securepassword'},
                    # Adicione mais propriedades conforme necessário
                },
            },
        },
    ],
    'responses': {
        201: {
            'description': 'User created successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    '_id': {'type': 'string', 'example': '5f45b40a808c7ce53d8d3f2a'},
                    'email': {'type': 'string', 'example': 'john.doe@example.com'},
                    'dataCreated': {'type': 'string', 'format': 'date-time', 'example': '2023-01-01T12:00:00Z'},
                    # Adicione mais propriedades conforme necessário
                },
            },
        },
        400: {
            'description': 'Bad Request - User with the same email already exists',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'User with the same email already exists'}},
            },
        },
        500: {
            'description': 'Internal Server Error - User creation failed or encountered an error',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'User creation failed'}},
            },
        },
    }
})
def create_user():
    """
    Create a new user.

    This endpoint allows the creation of a new user with the provided data.

    :return: Details of the created user.
    """
    try:
        # Get data from the request body
        data = request.get_json()

        # Check if the email already exists in the database
        existing_user = mongo.db.user.find_one({"email": data.get("email")})
        if existing_user:
            return jsonify({"message": "User with the same email already exists"}), 400

        # Generate current date
        data_created = datetime.datetime.now()

        # Check if password is present in the data
        if 'password' in data:
            # Hash the password before storing
            data['password'] = bcrypt.generate_password_hash(data['password']).decode('utf-8')

        # Insert data into the database, including the generated date
        result = mongo.db.user.insert_one({"dataCreated": data_created, **data})

        if result.acknowledged:
            # Return details of the created user (without the password)
            created_user = mongo.db.user.find_one({"_id": result.inserted_id})
            created_user["_id"] = str(created_user["_id"])
            del created_user["password"]
            user_data = {key: value.decode('utf-8', 'ignore') if isinstance(value, bytes) else value for key, value in created_user.items()}

            return jsonify(user_data), 201
        else:
            return jsonify({"message": "User creation failed"}), 500
    except Exception as error:
        print(error)
        return jsonify({"message": "User creation error"}), 500
    

# Login
@user_routes_bp.route('/login', methods=['POST'])
@swag_from({
    'operationId': 'login',
    'tags': ['user'],
    'parameters': [
        {
            'in': 'body',
            'name': 'login',
            'description': 'Credentials for user login',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'example': 'john.doe@example.com'},
                    'password': {'type': 'string', 'example': 'securepassword'},
                },
            },
        },
    ],
    'responses': {
        200: {
            'description': 'Login successful',
            'schema': {
                'type': 'object',
                'properties': {
                    'token': {'type': 'string', 'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1Zi40NWI0MGE4MDhjN2NlNTNkOGQzZjJhIiwiaWF0IjoxNjM5MTI3MzI1LCJleHAiOjE2MzkxMzEzMjV9.QyTCRrSR2rD63FGnCf-6H5iX37MZ45Yp2Gh1LBbwepY'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string', 'example': '5f45b40a808c7ce53d8d3f2a'},
                            'email': {'type': 'string', 'example': 'john.doe@example.com'},
                            # Adicione mais propriedades conforme necessário
                        },
                    },
                },
            },
        },
        401: {
            'description': 'Unauthorized - Invalid credentials',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Invalid credentials'}},
            },
        },
        500: {
            'description': 'Internal Server Error - Authentication error',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Authentication error'}},
            },
        },
    }
})
def login_user():
    """
    Authenticate and log in a user.

    This endpoint allows users to log in with their credentials.

    :return: Authentication token and user details.
    """
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")

        # Find the user by email
        user = mongo.db.user.find_one({"email": email})
        if user and bcrypt.check_password_hash(user["password"], password):
            # If credentials are correct, create an authentication token
            user_id_str = str(user["_id"])  # Convert ObjectId to string
            token_payload = {
                "sub": user_id_str,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
            }

            token = jwt.encode(token_payload, "your_secret_key_here", algorithm="HS256")

            # Remove the user's password before returning
            del user["password"]

            # Add the user ID string to the response JSON
            user["id"] = user_id_str

            return jsonify({"token": token, "user": user}), 200
        else:
            return jsonify({"message": "Invalid credentials"}), 401

    except Exception as error:
        print(error)
        return jsonify({"message": "Authentication error"}), 500

# List user using their token
@user_routes_bp.route('/users/byToken', methods=['GET'])
@jwt_required()  # Requires authentication with JWT token
@swag_from({
    'operationId': 'get_user_by_token',
    'tags': ['user'],
    'responses': {
        200: {
            'description': 'User profile details',
            'schema': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'email': {'type': 'string'},
                    # Add more properties as needed
                }
            }
        },
        401: {
            'description': 'Unauthorized - Invalid or expired token',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Permission denied. Invalid or expired token'}},
            },
        },
        404: {
            'description': 'User not found',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'User not found'}},
            },
        },
        500: {
            'description': 'Internal Server Error - Error getting user profile',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Error getting user profile'}},
            },
        },
    }
})
def get_user_profile():
    """
    Retrieve the profile of the authenticated user.

    This endpoint requires authentication with a valid JWT token.

    :return: User profile details.
    """
    try:
        current_user_id = get_jwt_identity()  # Get the ID of the authenticated user
        current_user_id_str = str(current_user_id)  # Convert ObjectId to string

        db = mongo.db
        user_collection = db['user']

        # Find the user in the database by ID
        user_data = user_collection.find_one({'_id': ObjectId(current_user_id_str)}, {'_id': 0, 'password': 0})

        if user_data:
            return jsonify(user_data), 200
        else:
            return jsonify({'message': 'User not found'}), 404

    except InvalidTokenError as e:
        # Handle JWT error, for example, invalid or expired token
        return jsonify({'message': 'Permission denied. Invalid or expired token'}), 401

    except Exception as e:
        return jsonify({'message': 'Error getting user profile'}), 500

# List user by code
@user_routes_bp.route('/users/<code>', methods=['GET'])
@swag_from({
    'operationId': 'get_user',
    'tags': ['user'],
    'parameters': [
        {
            'name': 'code',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Code of the user to retrieve',
        },
    ],
    'responses': {
        200: {
            'description': 'User details by code',
            'schema': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'email': {'type': 'string'},
                    # Add more properties as needed
                }
            }
        },
        404: {
            'description': 'User not found',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'User not found'}},
            },
        },
        500: {
            'description': 'Internal Server Error - Error getting user profile',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Error getting user profile'}},
            },
        },
    },

})
def get_user_code(code):
    """
    Retrieve the profile of a user by their code.

    :param code: Code of the user to retrieve.
    :return: User details by code.
    """
    try:
        db = mongo.db
        user_collection = db['user']

        # Find the user in the database by Code
        user_data = user_collection.find_one({'code': code}, {'_id': 0, 'password': 0})

        if user_data:
            return jsonify(user_data), 200
        else:
            return jsonify({'message': 'User not found'}), 404

    except Exception as e:
        return jsonify({'message': 'Error getting user profile'}), 500
    
# Delete user by code
@user_routes_bp.route('/users/<code>', methods=['DELETE'])
@swag_from({
    'operationId': 'delete_user',
    'tags': ['user'],
    'parameters': [
        {
            'name': 'code',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Code of the user to delete',
        },
    ],
    'responses': {
        200: {
            'description': 'User deleted successfully',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'User deleted successfully'}},
            },
        },
        404: {
            'description': 'User not found',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'User not found'}},
            },
        },
        500: {
            'description': 'Internal Server Error - Error deleting the user',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Error deleting the user'}},
            },
        },
    },
   
})
def delete_user(code):
    """
    Delete a user by their code.

    :param code: Code of the user to delete.
    :return: Status message indicating the success of the deletion.
    """
    try:
        db = mongo.db
        user_collection = db['user']

        # Find the user in the database by Code and delete
        result = user_collection.delete_one({'code': code})

        if result.deleted_count > 0:
            return jsonify({'message': 'User deleted successfully'}), 200
        else:
            return jsonify({'message': 'User not found'}), 404

    except Exception as e:
        return jsonify({'message': f'Error deleting the user: {str(e)}'}), 500


# Update a user by code
@user_routes_bp.route('/users/<code>', methods=['PUT'])
@swag_from({
    'operationId': 'update_user',
    'tags': ['user'],
    'parameters': [
        {
            'name': 'code',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Code of the user to update',
        },
    ],
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'username': {'type': 'string'},
                        'email': {'type': 'string'},
                        'password': {'type': 'string'},
                        # Add more properties as needed
                    },
                    'required': ['username', 'email'],  # Specify required properties
                }
            }
        },
        'description': 'JSON payload with user data to update',
    },
    'responses': {
        200: {
            'description': 'User updated successfully',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'User updated successfully'}},
            },
        },
        404: {
            'description': 'User not found',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'User not found'}},
            },
        },
        500: {
            'description': 'Internal Server Error - Error updating the user',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Error updating the user'}},
            },
        },
    },
    
})
def update_user(code):
    """
    Update a user by their code.

    :param code: Code of the user to update.
    :return: Status message indicating the success of the update.
    """
    try:
        db = mongo.db
        user_collection = db['user']

        # Check if the user exists before attempting to update
        existing_user = user_collection.find_one({'code': code})
        if not existing_user:
            return jsonify({'message': 'User not found'}), 404

        # Remove the '_id' field and, if the password is present, hash it
        request_data = request.get_json()
        if 'password' in request_data:
            request_data['password'] = bcrypt.generate_password_hash(request_data['password']).decode('utf-8')

        # Update the user in the database
        result = user_collection.update_one({'code': code}, {'$set': request_data})

        if result.modified_count > 0:
            return jsonify({'message': 'User updated successfully'}), 200
        else:
            return jsonify({'message': 'No modifications made'}), 200

    except Exception as e:
        return jsonify({'message': f'Error updating the user: {str(e)}'}), 500