from datetime import datetime, timedelta, timezone
from typing import Union

import jwt

# load env variables
from os import environ
from dotenv import load_dotenv
load_dotenv()

# Provide a default value
SECRET_KEY = environ.get("JWT_SECRET_KEY", "default_secret_key")
if SECRET_KEY is None:
    raise ValueError("JWT_SECRET_KEY environment variable is not set")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + \
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


if __name__ == "__main__":
    # Example usage
    token = create_access_token(data={"sub": "example_user"})
    print(token)
