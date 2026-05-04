"""
Quick test script for FastAPI application
Run: python test_api.py
"""
import requests

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check passed")

def test_create_order():
    """Test order creation"""
    data = {
        "id": "order-123",
        "user_id": "user-456",
        "amount": 99.99
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/orders",
        json=data
    )
    assert response.status_code == 200
    result = response.json()
    assert "saga_id" in result
    assert result["order_id"] == "order-123"
    print("✅ Create order passed")
    return result["order_id"]

def test_get_order(order_id: str):
    """Test getting order"""
    response = requests.get(f"{BASE_URL}/api/v1/orders/{order_id}")
    assert response.status_code == 200
    order = response.json()
    assert order["id"] == order_id
    assert order["status"] == "created"
    print("✅ Get order passed")

def test_cancel_order(order_id: str):
    """Test order cancellation"""
    data = {"reason": "Customer request"}
    response = requests.post(
        f"{BASE_URL}/api/v1/orders/{order_id}/cancel",
        json=data
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "cancelled"
    print("✅ Cancel order passed")

if __name__ == "__main__":
    print("🚀 Testing FastAPI application...\n")
    
    try:
        test_health()
        order_id = test_create_order()
        test_get_order(order_id)
        test_cancel_order(order_id)
        
        print("\n✅ All tests passed!")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to API. Make sure it's running:")
        print("   docker-compose up -d")
        print("   or")
        print("   uvicorn main:app --reload")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

