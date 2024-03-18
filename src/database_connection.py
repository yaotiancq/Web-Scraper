from pymongo import MongoClient
import datetime


class DatabaseManager:
    def __init__(self, mongo_host, mongo_port):
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port

    def connect_mongo(self, database_name, collection_name):
        self.database_name = database_name
        self.collection_name = collection_name
        uri = f"mongodb://{self.mongo_host}:{self.mongo_port}/"
        client = MongoClient(uri)
        db = client[self.database_name]
        collection = db[self.collection_name]
        return collection
    
    def insert(self, data):
        collection = self.connect_mongo(self.database_name, self.collection_name)
        if len(data) > 1:
            collection.insert_many(data)
        else:
            collection.insert_one(data[0])
    
    def find(self, query):
        collection = self.connect_mongo(self.database_name, self.collection_name)
        return collection.find(query)



def test_insert():
    example_time = datetime.datetime(2022, 2, 28, 12, 0, 0)
    d1 = {"project_id": 10002, "name": "tensorflow1", "owner_id": 90002, 
          "full_name": "dansuh171", "description": "1TensorFlow is an end-to-end open source platform for machine learning. It has a comprehensive, flexible ecosystem of tools, libraries, and community resources that lets researchers push the state-of-the-art in ML and developers easily build and deploy ML-powered applications.", 
          "html_url": "https://github.com/tensorflow/tensorflow", 
          "language": "python", "project_license": "Apache-2.0", "stars": 181001, "watchers": 7701, 
          "forks": 73701, "open_issues": "open_issues", "master_branch": "master_branch", 
          "default_branch": "default_branch", "created_at": example_time, "disabled": False, 
          "dependent_project_id": 2002, "dependency_project_id": 3002, "updated_at": example_time, 
          "pushed_at": example_time, "owner_name": "dansuh171", "releases": "releases", "token": "token"}
    
    d2 = {"project_id": 10003, "name": "tensorflow1", "owner_id": 90002, 
          "full_name": "dansuh171", "description": "1TensorFlow is an end-to-end open source platform for machine learning. It has a comprehensive, flexible ecosystem of tools, libraries, and community resources that lets researchers push the state-of-the-art in ML and developers easily build and deploy ML-powered applications.", 
          "html_url": "https://github.com/tensorflow/tensorflow", 
          "language": "python", "project_license": "Apache-2.0", "stars": 181001, "watchers": 7701, 
          "forks": 73701, "open_issues": "open_issues", "master_branch": "master_branch", 
          "default_branch": "default_branch", "created_at": example_time, "disabled": False, 
          "dependent_project_id": 2002, "dependency_project_id": 3002, "updated_at": example_time, 
          "pushed_at": example_time, "owner_name": "dansuh171", "releases": "releases", "token": "token"}

    d3 = {"project_id": 10004, "name": "tensorflow1", "owner_id": 90002, 
          "full_name": "dansuh171", "description": "1TensorFlow is an end-to-end open source platform for machine learning. It has a comprehensive, flexible ecosystem of tools, libraries, and community resources that lets researchers push the state-of-the-art in ML and developers easily build and deploy ML-powered applications.", 
          "html_url": "https://github.com/tensorflow/tensorflow", 
          "language": "python", "project_license": "Apache-2.0", "stars": 181001, "watchers": 7701, 
          "forks": 73701, "open_issues": "open_issues", "master_branch": "master_branch", 
          "default_branch": "default_branch", "created_at": example_time, "disabled": False, 
          "dependent_project_id": 2002, "dependency_project_id": 3002, "updated_at": example_time, 
          "pushed_at": example_time, "owner_name": "dansuh171", "releases": "releases", "token": "token"}
    data = [d1, d2]

    connection = DatabaseManager('3.139.100.241', 27017)
    connection.connect_mongo("test_database", "test_collection")
    connection.insert(data)
    connection.insert([d3])

if __name__ == "__main__":
    test_insert()
