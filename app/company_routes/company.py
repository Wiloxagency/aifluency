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

company_routes_bp = Blueprint('company_routes', __name__)
bcrypt = Bcrypt()

# List all companies
@company_routes_bp.route('/companies', methods=['GET'])
@swag_from({
    'operationId': 'get_companies',
    'tags': ['company'],
    'responses': {
        200: {
            'description': 'List of all companies',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'industry': {'type': 'string'},
                        # Add more properties as needed
                    }
                }
            }
        }
    }
})
def get_all_companies():
    """
    Retrieve a list of all companies.

    This function returns a list of companies, excluding the password.

    :return: List of companies.
    """
    # Retrieve and format the list of companies
    db = mongo.db
    collection = db['company'] 
    companies = list(collection.find({}, {'password': 0}))

    for company in companies:
        if "_id" in company:
            company["_id"] = str(company["_id"])

    return jsonify(companies)

# Create a company
@company_routes_bp.route('/companies', methods=['POST'])
@swag_from({
    'operationId': 'create_company',
    'tags': ['company'],  # Add the tag 'company' to the route
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'industry': {'type': 'string'},
                        # Add more properties as needed
                    },
                    'required': ['name', 'industry'],  # Specify required properties
                }
            }
        },
        'description': 'JSON payload with company data for creation',
    },
    'responses': {
        201: {
            'description': 'Company created successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    '_id': {'type': 'string', 'example': '609c6f2efbfeb07f8f7221a1'},
                    'name': {'type': 'string', 'example': 'Example Company'},
                    'industry': {'type': 'string', 'example': 'Technology'},
                    # Add more properties as needed
                }
            },
        },
        500: {
            'description': 'Internal Server Error - Company creation failed',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Company creation failed'}},
            },
        },
    },
})
def create_company():
    """
    Create a new company.

    :return: Details of the created company.
    """
    try:
        # Parse request data and generate creation date
        data = request.get_json()
        creationDate = datetime.datetime.now()

        # Insert data into the database
        result = mongo.db.company.insert_one({"creationDate": creationDate, **data})

        if result.acknowledged:
            # Return details of the created company
            created_company = mongo.db.company.find_one({"_id": result.inserted_id})
            created_company["_id"] = str(created_company["_id"])
            company_data = {key: value.decode('utf-8', 'ignore') if isinstance(value, bytes) else value for key, value in created_company.items()}

            return jsonify(company_data), 201
        else:
            return jsonify({"message": "Company creation failed"}), 500
    except Exception as error:
        print(error)
        return jsonify({"message": "Company creation error"}), 500


# Get company by code
@company_routes_bp.route('/companies/<code>', methods=['GET'])
@swag_from({
    'operationId': 'get_company',
    'tags': ['company'],  # Add the tag 'company' to the route
    'parameters': [
        {
            'name': 'code',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Code of the company to retrieve',
        },
    ],
    'responses': {
        200: {
            'description': 'Company details by code',
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'industry': {'type': 'string'},
                    # Add more properties as needed
                }
            }
        },
        404: {
            'description': 'Company not found',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Company not found'}},
            },
        },
        500: {
            'description': 'Internal Server Error - Error retrieving the company',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Error retrieving the company'}},
            },
        },
    }
})
def get_company_code(code):
    """
    Retrieve details of a company by its code.

    :param code: Code of the company to retrieve.
    :return: Company details by code.
    """
    try:
        db = mongo.db
        company_collection = db['company']

        # Retrieve company data from the database by code
        company_data = company_collection.find_one({'code': code}, {'_id': 0, 'password': 0})

        if company_data:
            return jsonify(company_data), 200
        else:
            return jsonify({'message': 'Company not found'}), 404

    except Exception as e:
        return jsonify({'message': 'Error retrieving the company'}), 500


# Delete company by code
@company_routes_bp.route('/companies/<code>', methods=['DELETE'])
@swag_from({
    'operationId': 'delete_company',
    'tags': ['company'],  # Add the tag 'company' to the route
    'parameters': [
        {
            'name': 'code',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Code of the company to delete',
        },
    ],
    'responses': {
        200: {
            'description': 'Company deleted successfully',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Company deleted successfully'}},
            },
        },
        400: {
            'description': 'Bad Request - Company has associated users',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'This company cannot be deleted as it has associated users.'}},
            },
        },
        404: {
            'description': 'Company not found',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Company not found'}},
            },
        },
        500: {
            'description': 'Internal Server Error - Error deleting the company',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Error deleting the company'}},
            },
        },
    }
})
def delete_company(code):
    """
    Delete a company by its code.

    :param code: Code of the company to delete.
    :return: Status message indicating the success of the deletion.
    """
    try:
        db = mongo.db
        company_collection = db['company']
        user_collection = db['user']

        # Check if users are associated with the company
        users_count = user_collection.count_documents({"code": code})

        if users_count > 0:
            return jsonify({"message": "This company cannot be deleted as it has associated users."}), 400

        # Delete the company
        result = company_collection.delete_one({"code": code})

        if result.deleted_count > 0:
            return jsonify({"message": "Company deleted successfully."}), 200
        else:
            return jsonify({"message": "Company not found."}), 404
    except Exception as e:
        return jsonify({"message": f"Error deleting the company: {str(e)}"}), 500
    
# Update company by code
@company_routes_bp.route('/companies/<code>', methods=['PUT'])
@swag_from({
    'operationId': 'update_company',
    'tags': ['company'],  # Add the tag 'company' to the route
    'parameters': [
        {
            'name': 'code',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Code of the company to update',
        },
    ],
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'industry': {'type': 'string'},
                        # Add more properties as needed
                    },
                    'required': [],  # Specify required properties if any
                }
            }
        },
        'description': 'JSON payload with updated company data',
    },
    'responses': {
        200: {
            'description': 'Company updated successfully',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Company updated successfully'}},
            },
        },
        404: {
            'description': 'Company not found or no data was modified',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Company not found or no data was modified'}},
            },
        },
        500: {
            'description': 'Internal Server Error - Error updating the company',
            'schema': {
                'type': 'object',
                'properties': {'message': {'type': 'string', 'example': 'Error updating the company'}},
            },
        },
    }
})
def update_company(code):
    """
    Update a company by its code.

    :param code: Code of the company to update.
    :return: Status message indicating the success of the update.
    """
    try:
        db = mongo.db
        company_collection = db['company']

        # Ensure _id is not present in update data
        request_data = request.get_json()
        if '_id' in request_data:
            del request_data['_id']

        # Update the company based on code
        result = company_collection.update_one(
            {"code": code},
            {"$set": request_data}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Company updated successfully."}), 200
        else:
            return jsonify({"message": "Company not found or no data was modified."}), 404

    except Exception as error:
        print(error)
        return jsonify({"message": "Error updating the company."}), 500