import functools
import logging
import time
import configparser
import os

import requests

"""
    A decorator for retrying a function if an exception is raised.

    Parameters:
    - retries (int): The maximum number of attempts.
    - backoff_factor (int): The factor by which the delay between attempts will increase.
"""
def retry(retries=3, backoff_factor=1):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper_retry(*args, **kwargs):
            _retries, _backoff_factor = retries, backoff_factor
            for attempt in range(1, retries + 1):
                try:
                    response = func(*args, **kwargs)
                    if response.status_code == 200:
                        return response
                except requests.exceptions.RequestException as e:
                    logging.warning(f"Attempt {attempt} failed: {e}")
                    if attempt == _retries:
                        raise
                    sleep_time = _backoff_factor * (2 ** (attempt - 1))
                    logging.warning(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)

        return wrapper_retry

    return decorator_retry


def load_config(config_file='config.ini'):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    config_path = os.path.join(root_dir, config_file)

    config = configparser.ConfigParser()
    config.read(config_path)
    return config


class GitHub_Api:
    """
        To use this class, you should add a config.ini file in the project root directory
    """

    def __init__(self, key=None):
        if key is None:
            config = load_config()
            self.key = config['github']['key']
        else:
            self.key = key
        self.parents = []

    """
        This query function will return an HTTP response, since the @retry decorator needs the HTTP status_code
        So you may need to convert the response to json before using

        Parameters:
        - query_type (str): GET or POST only.
        - url (str): The API URL of this query.
        - headers (dict): The headers of this query.
        - q (str): The payload of this query. It's optional.
    """
    @retry(retries=3, backoff_factor=1)
    def query(self, query_type, url, headers, q=None):

        if query_type == 'GET':
            response = requests.get(url, headers=headers)
        elif query_type == 'POST':
            response = requests.post(url, json={'query': q}, headers=headers)
        else:
            raise ValueError(f"Invalid query type: {query_type}")

        if response.status_code == 200:
            data = response.json()
            if 'errors' in data and len(data['errors']) > 0:
                # retry when the code is 200 but have errors in response
                if data['errors'][0]['message'] in ['loading', 'timeout']:
                    time.sleep(3)
                    return self.query(query_type, url, headers, q)
                else:
                    return response
            else:
                return response
        elif response.status_code < 500:
            # Log client-side errors and do not attempt retries
            error_message = f"Client error: HTTP status_code {response.status_code}"
            logging.error(error_message)
            raise RuntimeError(error_message)
        else:
            # For server-side errors, implement retry mechanism
            response.raise_for_status()

    """
        Search repo info by keyword

        Parameters:
        - query (str): The keyword of the repo. 
            (https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-repositories)
    """
    @functools.lru_cache(maxsize=1024)
    def search_repositories(self, query):

        url = 'https://api.github.com/search/repositories?q=' + query
        headers = {
            "Authorization": "Bearer {}".format(self.key),
            "Accept": "application/vnd.github+json"
        }

        results = self.query('GET', url, headers).json()
        if 'errors' in results and len(results['errors']) > 0:
            error_messages = '\n'.join([e['message'] for e in results['errors']])
            logging.error(error_messages)

        return results

    """
        Get repo info by its full name

        Parameters:
        - full_name (str): The full name of the repo. It should look like this: owner/repo_name.
            (https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository)
    """
    @functools.lru_cache(maxsize=1024)
    def get_repo_info(self, full_name):

        url = 'https://api.github.com/repos/' + full_name
        headers = {
            "Authorization": "Bearer {}".format(self.key),
            "Accept": "application/vnd.github+json"
        }

        results = self.query('GET', url, headers).json()
        if 'errors' in results and len(results['errors']) > 0:
            error_messages = '\n'.join([e['message'] for e in results['errors']])
            logging.error(error_messages)

        return results

    """
        Get repo release list by its full_name

        Parameters:
        - full_name (str): The full name of the repo. It should look like this: owner/repo_name.
    """
    @functools.lru_cache(maxsize=1024)
    def get_releases(self, full_name):

        url = 'https://api.github.com/repos/' + full_name + '/releases'
        headers = {
            "Authorization": "Bearer {}".format(self.key),
            "Accept": "application/vnd.github+json"
        }

        results = self.query('GET', url, headers).json()
        if 'errors' in results and len(results['errors']) > 0:
            error_messages = '\n'.join([e['message'] for e in results['errors']])
            logging.error(error_messages)

        return results

    @functools.lru_cache(maxsize=1024)
    def get_dependencies(self, repo_owner, repo_name, depth=1, lang=None):
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
    gh = GitHub_Api()
    gh.search_repositories('kitao/pyxel')
    gh.get_repo_info('kitao/pyxel')
    gh.get_releases('kitao/pyxel')
    for dep in gh.get_dependencies('kitao', 'pyxel', 2):
        indent = dep['level'] * "    "
        if dep['repository'] is not None:
            package = dep['repository']['nameWithOwner']
        else:
            package = dep['packageName']
        print(indent + package)
