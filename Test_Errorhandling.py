import unittest
from unittest.mock import patch
from Error_handling import GitHub_Api

class Test(unittest.TestCase):
    def setUp(self):
        self.api_key = "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"
        self.gh = GitHub_Api(key = self.api_key)

    @patch('Error_handling.requests.get')
    def test_get_repository(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"repository": "test_repository"}
        response = self.gh.get_repository("test_repo")
        self.assertEqual(response, {"repository": "test_repository"})

    @patch('Error_handling.requests.post')
    def test_get_dependencies(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"dependencies": "test_dependencies"}
        response = self.gh.get_dependencies("test_owner", "test_repo")
        self.assertEqual(response, {"dependencies": "test_dependencies"})


if __name__ == '__main__':
    unittest.main()