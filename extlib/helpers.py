import os
import re


def get_mongodb_uri():
    """
    get mongodb uri from env file
    :return: mongodb uri
    :rtype: str
    """

    mongo_uri_template = os.getenv('MONGO_DB_URI')
    username = os.getenv('MONGO_DB_USERNAME')
    password = os.getenv('MONGO_DB_PASSWORD')
    
    # safety check for environment variables
    if not all([mongo_uri_template, username, password]):
        missing_vars = []
        if not mongo_uri_template:
            missing_vars.append('MONGO_DB_URI')
        if not username:
            missing_vars.append('MONGO_DB_USERNAME')
        if not password:
            missing_vars.append('MONGO_DB_PASSWORD')
        raise ValueError(f"mongo db missing vars : {', '.join(missing_vars)}")
    
    mongo_uri = mongo_uri_template.replace('<db_username>', username).replace('<db_password>', password)
    
    # safety check for uri format
    uri_pattern = r"^mongodb(\+srv)?://[^:]+:[^@]+@[^/]+(/.+)?$"
    if not re.match(uri_pattern, mongo_uri):
        raise ValueError("MongoDB URI format is invalid. Please check the URI.")
    
    return mongo_uri