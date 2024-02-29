import functools
import logging
import time

import requests

class GitHub_Api:

    def __init__(self, key):
        self.key = key
        self.parents = []

    """
        This query function will return an HTTP response, since the @retry decorator needs the status_code
        So you may need to convert the response to json before use it

        Parameters:
        - query_type (str): GET or POST only.
        - url (str): The api url of this query.
        - headers (str): The head of this query.
        - q (str): The payload of this query. It's optional.
    """
    def query(self, query_type, url, headers, q=None):

        if query_type == 'GET':
            response = requests.get(url, headers=headers)
        elif query_type == 'POST':
            response = requests.post(url, json={'query': q}, headers=headers)
        else:
            print(f"Error query type: {query_type}")
            raise Exception()

        if response.status_code == 200:
            data = response.json()
            if 'errors' in data and len(data['errors']) > 0:
                # retry when the code is 200 but have errors in response
                if data['errors'][0]['message'] in ['loading', 'timeout']:
                    time.sleep(5)
                    return self.query(query_type, url, headers, q)
                else:
                    return response
            else:
                return response
        else:
            response.raise_for_status()

    """
        Get repo info by its full_name

        Parameters:
        - full_name (str): The full name of the repo. It should look like this: owner/repo_name.
    """
    @functools.lru_cache(maxsize=1024)
    def get_repository(self, full_name):

        url = 'https://api.github.com/search/repositories?q=' + full_name
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
        Get repo's dependencies
        - depth (int): It represents how many dependency levels you want to dive into
        - lang (str): It could filter the dependencies by its main language
    """
    @functools.lru_cache(maxsize=1024)
    def get_dependencies(self, repo_owner, repo_name, depth=1, lang=None):
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
        # one when a project have multiple dependencyGraphManifests
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


