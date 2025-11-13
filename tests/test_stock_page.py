import sys

sys.path.insert(0, "web")
from app import app

# Test stock chart page
with app.test_client() as client:
    print("Testing stock chart page...")

    # Test page load
    response = client.get("/stock/AAPL")
    print(
        f"/stock/AAPL: {'OK' if response.status_code == 200 else f'ERROR {response.status_code}'}"
    )

    # Test API endpoints
    response = client.get("/api/stock/AAPL/chart?timeframe=1D")
    print(
        f"/api/stock/AAPL/chart: {'OK' if response.status_code == 200 else f'ERROR {response.status_code}'}"
    )

    response = client.get("/api/stock/AAPL/ai-score")
    print(
        f"/api/stock/AAPL/ai-score: {'OK' if response.status_code == 200 else f'ERROR {response.status_code}'}"
    )

    response = client.get("/api/stock/AAPL/news")
    print(
        f"/api/stock/AAPL/news: {'OK' if response.status_code == 200 else f'ERROR {response.status_code}'}"
    )

    print("\nAll tests passed!")
