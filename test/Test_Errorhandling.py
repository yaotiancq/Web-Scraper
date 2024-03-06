import unittest
from unittest.mock import patch, MagicMock
from Error_handling import GitHub_Api

class TestGitHubApi(unittest.TestCase):
    @patch('Error_handling.requests')
    def test_get_repository_success(self, mock_requests):
        api = GitHub_Api(key='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')
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'name': 'test_repo'}
        mock_requests.get.return_value = mock_response

        result = api.get_repository('test_owner/test_repo')

        self.assertEqual(result, {'name': 'test_repo'})

    @patch('Error_handling.requests')
    def test_get_repository_failure(self, mock_requests):
        api = GitHub_Api(key='dummy_key')
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        with self.assertRaises(Exception):
            api.get_repository('test_owner/test_repo')

    @patch('Error_handling.requests')
    def test_get_dependencies_success(self, mock_requests):
        api = GitHub_Api(key='dummy_key')
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'repository': {'dependencyGraphManifests': {'nodes': []}}}}
        mock_requests.post.return_value = mock_response

        result = list(api.get_dependencies('test_owner', 'test_repo'))

        self.assertEqual(result, [])

    @patch('Error_handling.requests')
    def test_get_dependencies_failure(self, mock_requests):
        api = GitHub_Api(key='dummy_key')
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.post.return_value = mock_response

        with self.assertRaises(Exception):
            list(api.get_dependencies('test_owner', 'test_repo'))

if __name__ == '__main__':
    unittest.main()
