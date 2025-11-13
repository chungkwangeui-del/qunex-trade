import sys

sys.path.insert(0, "web")
from app import app

pages = [
    "/",
    "/market",
    "/screener",
    "/calendar",
    "/news",
    "/about",
    "/auth/login",
    "/auth/signup",
    "/auth/account",
    "/pricing",
    "/privacy",
    "/terms",
]

with app.test_client() as client:
    for page in pages:
        try:
            response = client.get(page)
            if response.status_code == 200:
                print(f"{page:20} OK")
            elif response.status_code == 302:
                print(f"{page:20} REDIRECT")
            elif response.status_code == 404:
                print(f"{page:20} NOT FOUND")
            else:
                print(f"{page:20} ERROR {response.status_code}")
        except Exception as e:
            error_str = str(e)
            if "TemplateSyntaxError" in error_str:
                print(f"{page:20} TEMPLATE ERROR")
                # Print the actual error
                print(f"  {error_str[:200]}")
            else:
                print(f"{page:20} EXCEPTION: {error_str[:80]}")
