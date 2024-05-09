from pymongo import MongoClient


class DatabaseManager:
    def __init__(self, mongo_host, mongo_port):
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port

    def connect_mongo(self, database_name, collection_name):
        """Connect to the database and collection, if the collection does not exist, 
            it will create one."""
        self.database_name = database_name
        self.collection_name = collection_name
        uri = f"mongodb://{self.mongo_host}:{self.mongo_port}/"
        client = MongoClient(uri)
        db = client[self.database_name]
        self.collection = db[self.collection_name]
        return self.collection
    
    def insert(self, data):
        """Insert data to the collection, data should be a list of dictionaries 
            even if it contains only one dictionary."""
        if len(data) > 1:
            self.collection.insert_many(data)
        else:
            self.collection.insert_one(data[0])

    # primitive method to find documents in the collection
    def _find(self, query):
        """Find documents in the collection, if query is not provided, it will return all documents.
        It returns a cursor object. You need to iterate over the cursor to get the documents."""
        return self.collection.find(query)
    
    def find(self, keyword=None, d=None, limit=-1, sort_by=None, sort_order=-1, skip=0, sort_by_array_size=None):
        """Find documents in the collection, if query is not provided, it will return all documents.
        It returns a list of dictionaries."""
        pipeline = []

        if d:
            pipeline.append({"$match": d})

        pipeline.append({
            "$addFields": {
                "nameMatch": {"$regexMatch": {"input": "$name", "regex": keyword, "options": "i"}},
                "descriptionMatch": {"$regexMatch": {"input": "$description", "regex": keyword, "options": "i"}},
                "ownerNameMatch": {"$regexMatch": {"input": "$owner_name", "regex": keyword, "options": "i"}},
            }
        })

        pipeline.append({
            "$addFields": {
                "sortPriority": {
                    "$cond": {
                        "if": "$nameMatch", "then": 1,
                        "else": {
                            "$cond": {
                                "if": "$descriptionMatch", "then": 2,
                                "else": {
                                    "$cond": {
                                        "if": "$ownerNameMatch", "then": 3,
                                        "else": 4
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })

        # add the size of the sorted field
        if sort_by_array_size:
            pipeline.append({
                "$addFields": {
                    "count_for_sort": {"$size": f"${sort_by_array_size}"}
                }
            })

        # Sort the results
        if sort_by:
            pipeline.append({"$sort": {sort_by: sort_order}})
        elif sort_by_array_size:
            pipeline.append({"$sort": {"count_for_sort": sort_order}})
        else:
            pipeline.append({"$sort": {"sortPriority": 1}})

        # Apply skip and limit
        if skip > 0:
            pipeline.append({"$skip": skip})
        if limit > 0:
            pipeline.append({"$limit": limit})

        # Execute the aggregation pipeline
        cursor = self.collection.aggregate(pipeline)
        return list(cursor)
          
    def _count(self, query):
        """Count the number of documents in the collection, if query is not provided, 
           it will return the total number of documents in the collection."""
        return self.collection.count_documents(query)
    
    def count(self, field='', value=''):
        if field and value:
            query = {field: value}
        else:
            query = {}
        return self.collection.count_documents(query)
    
    # remove document from the collection, if field and value are provided, 
    # it will remove the document with that field and value, otherwise it will remove all documents.
    def remove(self, field=None, value=None):
        if field and value:
            query = {field: value}
        else:
            query = {}
        self.collection.delete_one(query)

    def drop(self):
        collection = self.connect_mongo(self.database_name, self.collection_name)
        collection.drop()

    def _remove(self, query={}):
        """Remove documents from the collection, if query is not provided, 
           it will remove all documents"""
        self.collection.delete_many(query)
        
    def _update_target_field(self, query, new_query):
        """Update the target field in the document"""
        self.collection.update_one(query, {"$set": new_query})

    def _update_all_field(self, query, new_query):
        """Update the target document"""
        self.collection.update(query, new_query)

    def search_bar(self, keyword=None, language=None, project_license=None, limit_num=-1, category=None, sort_order=-1,
                   page=1, entryNum=10):
        """Search the collection based on the keyword, language, license, and category.
        It returns a list of dictionaries, also returns the total number of documents.
        If num is provided, it will return the number of documents specified by num.
        If category is provided, it will sort the documents based on the category.
        If page is provided, it will return the documents in that page."""
        query = {}
        entry_per_page = entryNum
        skip_row = (page - 1) * entry_per_page
        if language:
            query['language'] = language
        if project_license:
            query['project_license'] = {"$regex": project_license, "$options": "i"}
        if keyword:
            query['$or'] = [
                {"name": {"$regex": keyword, "$options": "i"}},
                {"description": {"$regex": keyword, "$options": "i"}},
                {"owner_name": {"$regex": keyword, "$options": "i"}}
            ]
        cnt = self._count(query)
        if category:
            if category == "Recent Updated":
                ans = self.find(keyword=keyword, d=query, sort_by='updated_at', sort_order=-1, limit=limit_num, skip=skip_row)[
                      :entry_per_page]
            elif category == "Most Popular":
                ans = self.find(keyword=keyword, d=query, sort_by='stars', sort_order=-1, limit=limit_num, skip=skip_row)[
                      :entry_per_page]
            elif category == "Least Dependencies":
                ans = self.find(keyword=keyword, d=query, sort_by_array_size='dependency_project_id', sort_order=1, limit=limit_num,
                                skip=skip_row)[:entry_per_page]
        else:
            ans = self.find(keyword=keyword, d=query, sort_by=category, sort_order=sort_order, limit=limit_num, skip=skip_row)[
                  :entry_per_page]
        return ans, cnt
        
def insertion_test():
    data=[{'project_id': 10000, 
           'name': 'xkcd2347', 'full_name': 'tom1', 'owner_id': 33829, 
           'owner_name': 'edsu', 'dependency_project_id': ['Baughn/python-diskcache', 'pytest-dev/pytest', 'theskumar/python-dotenv', 'yaml/pyyaml', 'psf/requests'], 
           'releases': [], 'description': 'Get dependencies for a project on GitHub.', 
           'project_license': 'MIT License', 'html_url': 'https://github.com/edsu/xkcd2347', 
           'language': 'Python', 'default_branch': 'master', 'master_branch': None, 
           'open_issues': 2, 'forks': 1, 'stars': 1200, 'watchers': 13, 'created_at': '2020-08-21T01:47:47Z', 
           'updated_at': '2024-01-18T09:05:33Z', 'pushed_at': '2021-06-17T17:32:26Z', 
           'created_at': '2020-08T17:32:26Z', 'disabled': False},
           {'project_id': 20000, 
           'name': 'xkcd2347', 'full_name': 'jack2', 'owner_id': 33829, 
           'owner_name': 'edsu', 'dependency_project_id': ['Baughn/python-diskcache', 'pytest-dev/pytest', 'theskumar/python-dotenv', 'yaml/pyyaml', 'psf/requests'], 
           'releases': [], 'description': 'Get dependencies for a project on GitHub.', 
           'project_license': 'MIT License', 'html_url': 'https://github.com/edsu/xkcd2347', 
           'language': 'Python', 'default_branch': 'master', 'master_branch': None, 
           'open_issues': 2, 'forks': 1, 'stars': 1000, 'watchers': 13, 'created_at': '2020-08-21T01:47:47Z', 
           'updated_at': '2024-01-18T09:05:33Z', 'pushed_at': '2021-06-17T17:32:26Z', 
           'created_at': '2020-08T17:32:26Z', 'disabled': False},
           {'project_id': 30000, 
           'name': 'xkcd2347', 'full_name': 'lily3', 'owner_id': 33829, 
           'owner_name': 'edsu', 'dependency_project_id': ['Baughn/python-diskcache', 'pytest-dev/pytest', 'theskumar/python-dotenv', 'yaml/pyyaml', 'psf/requests'], 
           'releases': [], 'description': 'Get dependencies for a project on GitHub.', 
           'project_license': 'MIT License', 'html_url': 'https://github.com/edsu/xkcd2347', 
           'language': 'Python', 'default_branch': 'master', 'master_branch': None, 
           'open_issues': 2, 'forks': 1, 'stars': 1500, 'watchers': 13, 'created_at': '2020-08-21T01:47:47Z', 
           'updated_at': '2024-01-18T09:05:33Z', 'pushed_at': '2021-06-17T17:32:26Z', 
           'created_at': '2020-08T17:32:26Z', 'disabled': False}
           ]
    db=DatabaseManager('3.139.100.241', 27017)
    db.connect_mongo("just_for_test", "just_for_test")
    db.insert(data)

def search_test():

    connection = DatabaseManager('3.139.100.241', 27017)
    connection.connect_mongo("test_database", "test_collection")

    # pagaination test
    # page=1
    # entryNum=10
    # res=connection.search_bar(category='stars',page=page, entryNum=entryNum)[0]
    # total=connection.search_bar(category='stars',page=page, entryNum=entryNum)[1]
    # for i in range(len(res)):
    #     print(res[i],'\t', (page-1)*entryNum+i+1,'/',total)

    # fuzzy search test
    print(connection.search_bar(keyword='dj',category='stars',page=1, entryNum=10)[0])
    

if __name__ == "__main__":
    # search_test()

    connection = DatabaseManager('3.139.100.241', 27017)
    connection.connect_mongo("test_database", "test_collection")
    print(connection._count({}))
    # connection.drop()

    # query = {"full_name": "django/django"}
    # result = list(connection._find(query).limit(20))
    # print(result)
