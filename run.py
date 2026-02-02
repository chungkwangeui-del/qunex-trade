import os
from web.app import create_app

app = create_app()

if __name__ == "__main__":
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
