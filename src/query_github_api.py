import functools
import logging
import time
import requests

class GitHub_Api:
    def __init__(self, key):
        self.key = key
        self.parents = []

    def query(self, query_type, url, headers, q = None, retries = 3):
        """
        Execute an HTTP request with retry and error handling.

        Parameters:
        - query_type (str): GET or POST only.
        - url (str): The API URL of this query.
        - headers (dict): The headers of this query.
        - q (str): The payload of this query. It's optional.
        - retries (int): Number of retries upon failure.

        Returns:
        - response: The HTTP response object.
        """
        for attempt in range(retries):
            try:
                if query_type == 'GET':
                    response = requests.get(url, headers = headers)
                elif query_type == 'POST':
                    response = requests.post(url, json = {'query': q}, headers = headers)
                else:
                    raise ValueError(f"Invalid query type: {query_type}")

                if response.status_code == 200:
                    data = response.json()
                    if 'errors' in data and len(data['errors']) > 0:
                        error_message = ', '.join([e['message'] for e in data['errors']])
                        logging.error(f"Error in response: {error_message}")
                        raise RuntimeError("Error in response")
                    else:
                        return response
                elif response.status_code >= 400 and response.status_code < 500:
                    error_message = f"Client error: {response.status_code}"
                    logging.error(error_message)
                    raise RuntimeError(error_message)
                elif response.status_code >= 500:
                    error_message = f"Server error: {response.status_code}"
                    logging.error(error_message)
                    if attempt < retries - 1:
                        wait_time = (2 ** attempt) * 0.5
                        logging.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError("Max retries exceeded")

            except requests.RequestException as e:
                logging.error(f"Request failed: {e}")
                if attempt < retries - 1:
                    wait_time = (2 ** attempt) * 0.5
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError("Max retries exceeded")

    @functools.lru_cache(maxsize = 1024)
    def get_repository(self, full_name):
        """
        Retrieve repository information by its full name.

        Parameters:
        - full_name (str): The full name of the repo. It should look like this: owner/repo_name.

        Returns:
        - results: Repository information in JSON format.
        """
        url = 'https://api.github.com/search/repositories?q=' + full_name
        headers = {
            "Authorization": "Bearer {}".format(self.key),
            "Accept": "application/vnd.github+json"
        }
        response = self.query('GET', url, headers)
        return response.json()

    @functools.lru_cache(maxsize = 1024)
    def get_dependencies(self, repo_owner, repo_name, depth = 1, lang = None):
        """
        Retrieve repository dependencies.

        Parameters:
        - repo_owner (str): The owner of the repository.
        - repo_name (str): The name of the repository.
        - depth (int): Number of dependency levels to retrieve.
        - lang (str): Language to filter dependencies (optional).

        Returns:
        - results: Repository dependency information in JSON format.
        """
        q = '''
            {
              repository(owner: "%s", name: "%s") {
                description
                dependencyGraphManifests(first: 50) {
                  nodes {
                    blobPath
                    dependencies {
                      nodes {
                        packageName
                        repository {
                          name
                          nameWithOwner
                          owner {
                            login
                          }
                          primaryLanguage {
                            name
                          }
                        }
                        requirements
                        hasDependencies
                      }
                    }
                  }
                }
              }
            }
            '''

        url = 'https://api.github.com/graphql'
        headers = {
            "Authorization": "Bearer {}".format(self.key),
            "Accept": "application/vnd.github.hawkgirl-preview+json"
        }

        response = self.query('POST', url, headers, q % (repo_owner, repo_name))
        return response.json()

"""
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    gh = GitHub_Api(key="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")

    try:
        gh.get_repository('wwwwwqqqqqq/GWU_CBES_Group3')
        for dep in gh.get_dependencies('wwwwwqqqqqq', 'GWU_CBES_Group3', 2):
            if isinstance(dep, dict):  # Check if 'dep' is a dictionary
                indent = dep.get('level', 0) * " "  # Use 'get' method to safely access 'level' key
                package = dep.get('repository', {}).get('nameWithOwner', '')  # Safely access nested keys
                print(indent + package)
            else:
                logging.warning(f"Unexpected data type: {type(dep)}")
    except RuntimeError as e:
        logging.error(f"Failed to retrieve data: {e}")
"""
