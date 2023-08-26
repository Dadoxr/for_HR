from tests.conftest import client, test_order_data


class TestRESTEndpoints:
    def test_get_all_orders(self, client):
        response = client.get("/rest/orders/all")
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)

    def test_create_order(self, client, test_order_data):
        response = client.post("/rest/orders", json=test_order_data)
        assert response.status_code == 201
        order = response.json()
        assert order["order_id"] == test_order_data["order_id"]
        assert order["user_id"] == test_order_data["user_id"]
        assert order["amount"] == test_order_data["amount"]
        assert order["status"] == "pending"

    def test_get_order_by_id(self, client, test_order_data):
        client.post("/rest/orders", json=test_order_data)

        response = client.get(f"/rest/orders/{test_order_data['order_id']}")
        assert response.status_code == 200
        order = response.json()
        assert order["order_id"] == test_order_data["order_id"]
        assert order["user_id"] == test_order_data["user_id"]

    def test_get_orders_by_user_id(self, client, test_order_data):
        client.post("/rest/orders", json=test_order_data)

        response = client.get(f"/rest/orders?user_id={test_order_data['user_id']}")
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        assert len(orders) > 0
        assert orders[0]["user_id"] == test_order_data["user_id"]

    def test_update_order(self, client, test_order_data):
        client.post("/rest/orders", json=test_order_data)

        update_data = {"status": "completed"}
        response = client.patch(
            f"/rest/orders/{test_order_data['order_id']}",
            json=update_data
        )
        assert response.status_code == 200
        order = response.json()
        assert order["status"] == "completed"

    def test_delete_order(self, client, test_order_data):
        client.post("/rest/orders", json=test_order_data)

        response = client.delete(f"/rest/orders/{test_order_data['order_id']}")
        assert response.status_code == 204

        get_response = client.get(f"/rest/orders/{test_order_data['order_id']}")
        assert get_response.status_code == 404

    def test_get_nonexistent_order(self, client):
        response = client.get("/rest/orders/nonexistent-order")
        assert response.status_code == 404

