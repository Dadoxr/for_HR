import pytest


class TestCQRSEndpoints:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Hello World"

    @pytest.mark.asyncio
    async def test_create_order_command(self, client, test_order_data):
        data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"],
        }
        response = await client.post("/api/v1/orders", json=data)
        assert response.status_code == 201
        result = response.json()
        assert "saga_id" in result
        assert result["order_id"] == test_order_data["order_id"]

    @pytest.mark.asyncio
    async def test_get_order_query(self, client, test_order_data):
        create_data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"],
        }
        await client.post("/api/v1/orders", json=create_data)

        response = await client.get(f"/api/v1/orders/{test_order_data['order_id']}")
        assert response.status_code == 200
        order = response.json()
        assert order["id"] == test_order_data["order_id"]
        assert order["status"] in ["created", "pending"]

    @pytest.mark.asyncio
    async def test_list_orders_query(self, client, test_order_data):
        create_data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"],
        }
        await client.post("/api/v1/orders", json=create_data)

        response = await client.get(
            f"/api/v1/orders?user_id={test_order_data['user_id']}"
        )
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        assert len(orders) >= 1
        assert any(o["id"] == test_order_data["order_id"] for o in orders)

    @pytest.mark.asyncio
    async def test_list_orders_empty_for_unknown_user(self, client):
        response = await client.get("/api/v1/orders?user_id=nonexistent-user-999")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_event_replay_reflects_status_changes(self, client, test_order_data):
        """Create order, then cancel - event replay should show final state."""
        create_data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"],
        }
        await client.post("/api/v1/orders", json=create_data)

        response = await client.get(f"/api/v1/orders/{test_order_data['order_id']}")
        assert response.json()["status"] in ["created", "pending"]

        await client.post(
            f"/api/v1/orders/{test_order_data['order_id']}/cancel",
            json={"reason": "changed mind"},
        )

        response = await client.get(f"/api/v1/orders/{test_order_data['order_id']}")
        assert response.json()["status"] == "cancelled"
        assert response.json()["cancel_reason"] == "changed mind"

    @pytest.mark.asyncio
    async def test_cancel_order_command(self, client, test_order_data):
        create_data = {
            "id": test_order_data["order_id"],
            "user_id": test_order_data["user_id"],
            "amount": test_order_data["amount"],
        }
        await client.post("/api/v1/orders", json=create_data)

        cancel_data = {"reason": "Test cancellation"}
        response = await client.post(
            f"/api/v1/orders/{test_order_data['order_id']}/cancel",
            json=cancel_data,
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "cancelled"
        assert result["order_id"] == test_order_data["order_id"]
