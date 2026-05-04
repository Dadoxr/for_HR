import pytest


class TestRESTEndpoints:
    @pytest.mark.asyncio
    async def test_get_all_orders(self, client):
        response = await client.get("/rest/orders/all")
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_create_order(self, client, test_order_data):
        response = await client.post("/rest/orders", json=test_order_data)
        assert response.status_code == 201
        order = response.json()
        assert order["order_id"] == test_order_data["order_id"]
        assert order["user_id"] == test_order_data["user_id"]
        assert float(order["amount"]) == test_order_data["amount"]
        assert order["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_order_by_id(self, client, test_order_data):
        await client.post("/rest/orders", json=test_order_data)

        response = await client.get(f"/rest/orders/{test_order_data['order_id']}")
        assert response.status_code == 200
        order = response.json()
        assert order["order_id"] == test_order_data["order_id"]
        assert order["user_id"] == test_order_data["user_id"]

    @pytest.mark.asyncio
    async def test_get_orders_by_user_id(self, client, test_order_data):
        await client.post("/rest/orders", json=test_order_data)

        response = await client.get(f"/rest/orders?user_id={test_order_data['user_id']}")
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        assert len(orders) > 0
        assert orders[0]["user_id"] == test_order_data["user_id"]

    @pytest.mark.asyncio
    async def test_update_order(self, client, test_order_data):
        await client.post("/rest/orders", json=test_order_data)

        update_data = {"status": "completed"}
        response = await client.patch(
            f"/rest/orders/{test_order_data['order_id']}",
            json=update_data,
        )
        assert response.status_code == 200
        order = response.json()
        assert order["status"] == "completed"

    @pytest.mark.asyncio
    async def test_delete_order(self, client, test_order_data):
        await client.post("/rest/orders", json=test_order_data)

        response = await client.delete(f"/rest/orders/{test_order_data['order_id']}")
        assert response.status_code == 204

        get_response = await client.get(f"/rest/orders/{test_order_data['order_id']}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_order(self, client):
        response = await client.get("/rest/orders/nonexistent-order")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_order(self, client):
        response = await client.delete("/rest/orders/nonexistent-id-999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_order(self, client):
        response = await client.patch(
            "/rest/orders/nonexistent-id-999", json={"status": "completed"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_and_list_multiple_orders(self, client):
        """Create multiple orders, verify all appear in list."""
        orders_data = [
            {"order_id": f"order-{i}", "user_id": "bulk-user", "amount": 10.0 * i + 0.01}
            for i in range(1, 4)
        ]
        for data in orders_data:
            resp = await client.post("/rest/orders", json=data)
            assert resp.status_code == 201

        response = await client.get("/rest/orders?user_id=bulk-user")
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) == 3

    @pytest.mark.asyncio
    async def test_update_preserves_other_fields(self, client, test_order_data):
        """Updating status should not erase other fields."""
        await client.post("/rest/orders", json=test_order_data)

        await client.patch(
            f"/rest/orders/{test_order_data['order_id']}",
            json={"status": "shipped"},
        )

        response = await client.get(f"/rest/orders/{test_order_data['order_id']}")
        order = response.json()
        assert order["status"] == "shipped"
        assert order["user_id"] == test_order_data["user_id"]
        assert float(order["amount"]) == test_order_data["amount"]
