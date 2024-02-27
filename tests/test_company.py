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
        mongo.db.company.delete_many({"code": "123"})
        mongo.db.user.delete_many({"email": "wilox@gmail.com"})

    def json_default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        raise TypeError("Object of type {} is not JSON serializable".format(type(obj)))
    
    def test_create_company_success(self):
        # Request to create a company
        response = self.app.post('/companies', json={"name": "wilox", "code": "123"})
        data = response.get_json()

        # Check if the response indicates successful company creation (status code 201)
        self.assertEqual(response.status_code, 201)
        self.assertIn("_id", data)
        self.assertIn("name", data)
        self.assertIn("code", data)

    def test_create_company_internal_error(self):
        # Mock an exception to simulate an internal error in the create_company function
        with patch('pymongo.collection.Collection.insert_one') as mock_insert_one:
            mock_insert_one.side_effect = Exception("Simulated database error")

            # Request to create a company should result in a failure (status code 500)
            response = self.app.post('/companies', json={"name": "wilox", "code": "123"})
            data = response.get_json()

            # Check if the response indicates a company creation failure (status code 500)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(data["message"], "Company creation error")

    def test_get_company_code_not_found(self):
            # Test to retrieve company data for a non-existent company code
            response = self.app.get('/companies/111')
            data = response.get_json()

            self.assertEqual(response.status_code, 404)
            self.assertEqual(data["message"], "Company not found")

    def test_delete_company_success(self):
        # Crie uma empresa para o teste
        self.app.post('/companies', json={"name": "wilox", "code": "123"})

        # Teste para excluir a empresa
        response = self.app.delete('/companies/123')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["message"], "Company deleted successfully.")

    def test_delete_company_associated_users(self):
        # Crie uma empresa e associe um usuário a ela para o teste
        self.app.post('/companies', json={"name": "wilox", "code": "123"})
        self.app.post('/users', json={"email": "wilox@gmail.com", "code": "123"})

        # Tente excluir a empresa com usuários associados
        response = self.app.delete('/companies/123')
        data = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["message"], "This company cannot be deleted as it has associated users.")

    def test_delete_company_not_found(self):
        # Tente excluir uma empresa inexistente
        response = self.app.delete('/companies/nonexistentcode')
        data = response.get_json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(data["message"], "Company not found.")

    def test_update_company_success(self):
        # Crie uma empresa para o teste
        self.app.post('/companies', json={"name": "wilox", "code": "123"})

        # Atualize os detalhes da empresa
        response = self.app.put('/companies/123', json={"name": "Updated Company"})
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["message"], "Company updated successfully.")

    def test_update_company_not_found(self):
        # Tente atualizar uma empresa que não existe
        response = self.app.put('/companies/nonexistentcode', json={"name": "Updated Company"})
        data = response.get_json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(data["message"], "Company not found or no data was modified.")

    def test_update_company_internal_error(self):
        # Force um erro interno durante a atualização
        with patch('pymongo.collection.Collection.update_one') as mock_update_one:
            mock_update_one.side_effect = Exception("Simulated database update error")

            # Tente atualizar uma empresa
            response = self.app.put('/companies/test123', json={"name": "Updated Company"})
            data = response.get_json()

            self.assertEqual(response.status_code, 500)
            self.assertEqual(data["message"], "Error updating the company.")




