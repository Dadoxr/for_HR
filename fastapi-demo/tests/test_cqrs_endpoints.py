from tests.conftest import client, test_order_data


class TestCQRSEndpoints:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Hello World"

    def test_create_order_command(self, client, test_order_data):
        data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"]
        }
        response = client.post("/api/v1/orders", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "saga_id" in result
        assert result["order_id"] == test_order_data["order_id"]

    def test_get_order_query(self, client, test_order_data):
        create_data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"]
        }
        client.post("/api/v1/orders", json=create_data)

        response = client.get(f"/api/v1/orders/{test_order_data['order_id']}")
        assert response.status_code == 200
        order = response.json()
        assert order["id"] == test_order_data["order_id"]
        assert order["status"] in ["created", "pending"]

    def test_list_orders_query(self, client, test_order_data):
        create_data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"]
        }
        client.post("/api/v1/orders", json=create_data)

        response = client.get(f"/api/v1/orders?user_id={test_order_data['user_id']}")
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)

    def test_cancel_order_command(self, client, test_order_data):
        create_data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"]
        }
        client.post("/api/v1/orders", json=create_data)

        cancel_data = {"reason": "Test cancellation"}
        response = client.post(
            f"/api/v1/orders/{test_order_data['order_id']}/cancel",
            json=cancel_data
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "cancelled"
        assert result["order_id"] == test_order_data["order_id"]

