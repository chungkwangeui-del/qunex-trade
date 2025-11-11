import sys
import traceback
sys.path.insert(0, 'web')

try:
    from app import app

    with app.test_client() as client:
        print("Testing /screener...")
        response = client.get('/screener')
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("SUCCESS - Page loads correctly!")
            print(f"Content length: {len(response.data)} bytes")
        else:
            print(f"ERROR - Status {response.status_code}")
            print(response.data[:500].decode('utf-8', errors='ignore'))

except Exception as e:
    print(f"\nEXCEPTION occurred:")
    print("=" * 60)
    traceback.print_exc()
    print("=" * 60)
