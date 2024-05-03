import logging
import time
from collections import deque
from threading import Thread, Lock

import convert_and_assemble
from database_connection import DatabaseManager
from src.query_github_api import GitHub_Api

lock = Lock()


def search_and_save(query):
    """
        Search repos via constructed query and save the assembled info into DB

        doc:
            (https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#constructing-a-search-query)
    """
    client = GitHub_Api()
    try:
        search_results = client.search_repositories(query)
    except Exception as e:
        logging.error(f"Failed to search query: {query} due to: {e}")
        return -1

    if search_results is None:
        logging.error(f"Search result for query: {query} is None.")
        return 0

    queue = deque(item['full_name'] for item in search_results['items'])  # Only keep their full_name
    seen = set()  # de-duplicate repos

    # DB client
    connection = DatabaseManager('3.139.100.241', 27018)
    connection.connect_mongo("test_database", "test_collection")  # TODO update DB info

    count_root = len(queue)
    count = 0
    while queue:
        cur = queue.popleft()
        count += 1
        if cur in seen:
            continue
        seen.add(cur)

        # checking if this repo exists in DB
        # query = {"full_name": cur}
        # result = list(connection._find(query))
        # if result is not None and len(result) > 0:
        #     logging.warning(f"Repository {cur} already exists, skipping...")
        #     continue

        try:
            assembled_result = convert_and_assemble.assemble_api_response(cur)
            if assembled_result is None:
                logging.warning(f"No assembled result for {cur}, skipping...")
                continue

            if count <= count_root and len(assembled_result['dependency_project_id']) == 0:
                logging.info(f"No dependencies found for repo: {assembled_result['full_name']}")
                continue

            # checking if this repo exists in DB
            query = {"full_name": cur}
            result = list(connection._find(query))
            if result is not None and len(result) > 0:
                # update existing data and continue
                connection._update_target_field(query, assembled_result)
                print(f"Update repository info: {cur}")
                continue

            # Insert the assembled_result into DB
            connection.insert([assembled_result])
            print(f"Insert repo info: {cur}")
            logging.info(f"Insert repository info: {cur}")

            # Add the dependencies of the current repo to wait-list
            for dependency in assembled_result['dependency_project_id']:
                if dependency['full_name'] not in seen:  # Prevent re-adding seen dependencies
                    queue.append(dependency['full_name'])
        except Exception as e:
            logging.error(f"Error processing repo {cur}: {e}")
            continue

    return 1


def update_database():
    queries = [
        'language%3AC%2B%2B+&sort=stars&per_page=10',
        'language%3AC%2B%2B+&sort=forks&per_page=10',
        'language%3AC%2B%2B+&sort=help-wanted-issues&per_page=10',
        'language%3AC%2B%2B+&sort=updated&per_page=10',
        'language%3AC+&sort=stars&per_page=10',
        'language%3AC+&sort=forks&per_page=10',
        'language%3AC+&sort=help-wanted-issues&per_page=10',
        'language%3AC+&sort=updated&per_page=10'
    ]
    if lock.acquire(blocking=False):
        try:
            for query_base in queries:
                page = 1
                while True:
                    query = f'{query_base}&page={page}'
                    result = search_and_save(query)
                    if result == 0 or page > 100:
                        break
                    page += result
                time.sleep(20)
        finally:
            lock.release()
    else:
        logging.warning("update_database is already running.")


def start_update_database():
    if not lock.locked():
        Thread(target=update_database).start()
        return "Database update started successfully."
    else:
        return "Update is already running. Please do not call again."


if __name__ == "__main__":
    # search_and_save('gwu+in:name+language%3AC%2B%2B+language%3AC+&sort=stars&per_page=100&page=1')
    update_database()
