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
                    response = requests.get(url, headers=headers)
                elif query_type == 'POST':
                    response = requests.post(url, json={'query': q}, headers=headers)
                else:
                    raise ValueError(f"Invalid query type: {query_type}")

                if response.status_code >= 400:
                    # Log client-side errors and do not attempt retries
                    if response.status_code < 500:
                        error_message = f"Client error: {response.status_code}"
                        logging.error(error_message)
                        raise RuntimeError(error_message)
                    # For server-side errors, implement retry mechanism
                    elif attempt < retries - 1:
                        error_message = f"Server error: {response.status_code}"
                        logging.error(error_message)
                        wait_time = (2 ** attempt) * 0.5  # Exponential backoff
                        logging.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError("Max retries exceeded")

                return response

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

        results = self.query('POST', url, headers, q % (repo_owner, repo_name)).json()
        if 'errors' in results and len(results['errors']) > 0:
            error_messages = '\n'.join([e['message'] for e in results['errors']])
            logging.error(error_messages)
            return  # Return None if there are errors

        # visited is used to prevent a given dependency from being reported more than
        # one when a project has multiple dependencyGraphManifests
        visited = set()

        for m in results['data']['repository']['dependencyGraphManifests']['nodes']:
            for dep in m['dependencies']['nodes']:
                dep['level'] = len(self.parents)

                if lang and dep['repository'] and dep['repository']['primaryLanguage'] and \
                        dep['repository']['primaryLanguage']['name'].lower() != lang.lower():
                    continue

                if dep['packageName'] in visited:
                    continue

                visited.add(dep['packageName'])
                yield dep

                if (depth == 0 or len(self.parents) + 1 < depth) and dep['hasDependencies'] == True and dep[
                    'repository']:
                    # prevent an infinite loop from circular dependencies
                    dep_id = '{}/{}/{}'.format(
                        dep['repository']['owner']['login'],
                        dep['repository']['name'],
                        dep['packageName']
                    )
                    if dep_id not in self.parents:
                        self.parents.append(dep_id)
                        yield from self.get_dependencies(
                            dep['repository']['owner']['login'],
                            dep['repository']['name'],
                            depth,
                            lang
                        )
                        self.parents.pop()


if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)

    gh = GitHub_Api(key = "123")

    try:
        gh.get_repository('Netflix/eureka')
        for dep in gh.get_dependencies('wwwwwqqqqqq', 'GWU_CBES_Group3', 2):
            if isinstance(dep, dict):  # Check if 'dep' is a dictionary
                indent = dep.get('level', 0) * " "  # Use 'get' method to safely access 'level' key
                package = dep.get('repository', {}).get('nameWithOwner', '')  # Safely access nested keys
                print(indent + package)
            else:
                logging.warning(f"Unexpected data type: {type(dep)}")
    except RuntimeError as e:
        logging.error(f"Failed to retrieve data: {e}")
