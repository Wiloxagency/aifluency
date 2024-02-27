import unittest
from app import create_app
from unittest.mock import patch
from config.db import mongo
from bson import ObjectId, json_util

class TestUserRoutes(unittest.TestCase):
    def setUp(self):
        # Use mongomock for testing instead of a real database
        patcher = patch('pymongo.MongoClient')
        self.mock_mongo_client = patcher.start()
        self.addCleanup(patcher.stop)

        # Indicate that it's in testing mode when creating the app
        self.app = create_app(testing=True).test_client()

    def tearDown(self):
        # Clear the database after each test
        self.mock_mongo_client.reset_mock()
        # Delete test data or perform necessary cleanup
        mongo.db.user.delete_many({"email": "test@example.com"})

    def json_default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        raise TypeError("Object of type {} is not JSON serializable".format(type(obj)))

    def test_create_user(self):
        # Test user creation
        response = self.app.post('/users', json={"email": "test@example.com", "password": "test123"})
        data = response.get_json()

        self.assertEqual(response.status_code, 201)
        self.assertIn("_id", data)
        self.assertIn("dataCreated", data)
        self.assertIn("email", data)

        # Trying to create a user with the same email should return an error
        response_existing_user = self.app.post('/users', json={"email": "test@example.com", "password": "test123"})
        data_existing_user = response_existing_user.get_json()

        self.assertEqual(response_existing_user.status_code, 400)
        self.assertEqual(data_existing_user["message"], "User with the same email already exists")

        # Add tests to handle specific errors from the create_user function
        # For example, simulate a failure during database insertion

        with patch('pymongo.collection.Collection.insert_one') as mock_insert_one:
            # Set up the mock to simulate an insertion failure
            mock_insert_one.side_effect = Exception("Simulated database insertion error")

            # Trying to create a user should return a 500 error
            response_error = self.app.post('/users', json={"email": "another@example.com", "password": "test123"})
            data_error = response_error.get_json()

            self.assertEqual(response_error.status_code, 500)
            self.assertEqual(data_error["message"], "User creation error")

    def test_get_all_users(self):
        # Create a user for the test
        self.app.post('/users', json={"email": "test@example.com", "password": "test123"})

        # Test to get all users
        response = self.app.get('/users')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(data, list)

    def test_login_user(self):
        # Create a user for the test
        self.app.post('/users', json={"email": "test@example.com", "password": "test123"})

        # The test to log in with correct credentials
        response = self.app.post('/login', json={"email": "test@example.com", "password": "test123"})
        data = response.get_json()

        # Update the assertion to use the updated json_default method
        self.assertEqual(response.status_code, 200, data)
        self.assertIn("token", data)
        self.assertIn("user", data)
        self.assertIn("id", data["user"])

        # Test to log in with incorrect credentials
        response_invalid_credentials = self.app.post('/login', json={"email": "test@example.com", "password": "wrongpassword"})
        data_invalid_credentials = response_invalid_credentials.get_json()

        self.assertEqual(response_invalid_credentials.status_code, 401)
        self.assertEqual(data_invalid_credentials["message"], "Invalid credentials")

        # Error 500
        response_invalid_credentials = self.app.post('/login', json={"email": "test@example.com", "passwords": "wrongpassword"})
        data_invalid_credentials = response_invalid_credentials.get_json()

        self.assertEqual(response_invalid_credentials.status_code, 500)
        self.assertEqual(data_invalid_credentials["message"], "Authentication error")

    def test_get_user_profile(self):
        # Create a user for the test
        response_create_user = self.app.post('/users', json={"email": "test@example.com", "password": "test123"})

        # Check if the user creation was successful (status code 201)
        self.assertEqual(response_create_user.status_code, 201)

        # Log in with the user to obtain the token
        response_login = self.app.post('/login', json={"email": "test@example.com", "password": "test123"})
        data_login = response_login.get_json()
        token = data_login["token"]

        # Set the authorization header with the obtained token
        headers = {"Authorization": f"Bearer {token}"}

        # Make a request to the /user endpoint
        response_get_user_profile = self.app.get('/user', headers=headers)
        data_get_user_profile = response_get_user_profile.get_json()

        # Check if the response contains the expected information
        self.assertEqual(response_get_user_profile.status_code, 200)
        self.assertIn("email", data_get_user_profile)
        self.assertIn("dataCreated", data_get_user_profile)
        self.assertNotIn("password", data_get_user_profile)

    def test_get_user_profile_invalid_token(self):
        # Try to access the /user endpoint with an invalid token
        headers_invalid_token = {"Authorization": "Bearer invalid_token"}
        response_invalid_token = self.app.get('/user', headers=headers_invalid_token)

        # Check if the response indicates a permission error
        self.assertEqual(response_invalid_token.status_code, 422)

    def test_get_user_code(self):
        # Create a user for the test with a specific code
        response_create_user = self.app.post('/users', json={"email": "test@example.com", "password": "test123", "code": "test123"})

        # Check if the user creation was successful (status code 201)
        self.assertEqual(response_create_user.status_code, 201)

        # Make a request to the /user/test123 endpoint
        response_get_user_code = self.app.get('/user/test123')
        data_get_user_code = response_get_user_code.get_json()

        # Check if the response contains the expected information
        self.assertEqual(response_get_user_code.status_code, 200)
        self.assertIn("email", data_get_user_code)
        self.assertIn("code", data_get_user_code)
        self.assertNotIn("password", data_get_user_code)

    def test_get_user_code_not_found(self):
        # Make a request to the /user/nonexistent endpoint
        response_get_user_code = self.app.get('/user/nonexistent')
        data_get_user_code = response_get_user_code.get_json()

        # Check if the response indicates that the user was not found (status code 404)
        self.assertEqual(response_get_user_code.status_code, 404)
        self.assertEqual(data_get_user_code["message"], "User not found")

    def test_get_user_code_internal_error(self):
        # Create a user for the test with a specific code
        response_create_user = self.app.post('/users', json={"email": "test@example.com", "password": "test123", "code": "test123"})

        # Check if the user creation was successful (status code 201)
        self.assertEqual(response_create_user.status_code, 201)

        # Mock an exception to simulate an internal error in the get_user_code function
        with patch('pymongo.collection.Collection.find_one') as mock_find_one:
            mock_find_one.side_effect = Exception("Simulated database error")

            # Make a request to the /user/test123 endpoint
            response_get_user_code = self.app.get('/user/test123')
            data_get_user_code = response_get_user_code.get_json()

            # Check if the response indicates an internal server error (status code 500)
            self.assertEqual(response_get_user_code.status_code, 500)
            self.assertEqual(data_get_user_code["message"], "Error getting user profile")

    def test_delete_user_success(self):
        # Create a user for the test with a specific code
        response_create_user = self.app.post('/users', json={"email": "test@example.com", "password": "test123", "code": "test123"})

        # Check if the user creation was successful (status code 201)
        self.assertEqual(response_create_user.status_code, 201)

        # Make a request to the /user/test123 endpoint to delete the user
        response_delete_user = self.app.delete('/user/test123')
        data_delete_user = response_delete_user.get_json()

        # Check if the response indicates successful user deletion (status code 200)
        self.assertEqual(response_delete_user.status_code, 200)
        self.assertEqual(data_delete_user["message"], "User deleted successfully")

    def test_delete_user_not_found(self):
        # Make a request to delete a non-existent user (status code 404)
        response_delete_user = self.app.delete('/user/inexistent')
        data_delete_user = response_delete_user.get_json()

        # Check if the response indicates that the user was not found (status code 404)
        self.assertEqual(response_delete_user.status_code, 404)
        self.assertEqual(data_delete_user["message"], "User not found")

    def test_delete_user_internal_error(self):
        # Mock an exception to simulate an internal error in the delete_user function
        with patch('pymongo.collection.Collection.delete_one') as mock_delete_one:
            mock_delete_one.side_effect = Exception("Simulated database error")

            # Make a request to the /user/test123 endpoint to delete the user
            response_delete_user = self.app.delete('/user/test123')
            data_delete_user = response_delete_user.get_json()

            # Check if the response indicates an internal server error (status code 500)
            self.assertEqual(response_delete_user.status_code, 500)
            self.assertEqual(data_delete_user["message"], "Error deleting the user: Simulated database error")

    def test_update_user_success(self):
        # Create a user for the test with a specific code
        response_create_user = self.app.post('/users', json={"email": "test@example.com", "password": "test123", "code": "test123"})

        # Check if the user creation was successful (status code 201)
        self.assertEqual(response_create_user.status_code, 201)

        # Make a request to update the user at the /user/test123 endpoint
        response_update_user = self.app.put('/user/test123', json={"email": "updated@example.com", "password": "updated123"})
        data_update_user = response_update_user.get_json()

        # Check if the response indicates successful user update (status code 200)
        self.assertEqual(response_update_user.status_code, 200)
        self.assertEqual(data_update_user["message"], "User updated successfully")

    def test_update_user_not_found(self):
        # Make a request to update a non-existent user (status code 404)
        response_update_user = self.app.put('/user/inexistent', json={"email": "updated@example.com", "password": "updated123"})
        data_update_user = response_update_user.get_json()

        # Check if the response indicates that the user was not found (status code 404)
        self.assertEqual(response_update_user.status_code, 404)
        self.assertEqual(data_update_user["message"], "User not found")

    def test_update_user_internal_error(self):
        # Mock an exception to simulate an internal error in the update_user function
        with patch('pymongo.collection.Collection.update_one') as mock_update_one:
            mock_update_one.side_effect = Exception("Simulated database error")

            # Make a request to update the user at the /user/test123 endpoint
            response_update_user = self.app.put('/user/test123', json={"email": "updated@example.com", "password": "updated123"})
            data_update_user = response_update_user.get_json()

            # Check if the response indicates an internal server error (status code 500)
            self.assertEqual(response_update_user.status_code, 500)
            self.assertEqual(data_update_user["message"], "Error updating the user: Simulated database error")


if __name__ == '__main__':
    unittest.main()