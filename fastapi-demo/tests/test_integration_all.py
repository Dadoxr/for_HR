import pytest


class TestIntegrationAll:
    @pytest.mark.asyncio
    async def test_full_order_lifecycle(self, client, test_order_data):
        order_id = test_order_data["order_id"]
        user_id = test_order_data["user_id"]

        # CQRS: create order
        cqrs_create = {
            "id": order_id,
            "user_id": user_id,
            "amount": test_order_data["amount"],
        }
        response = await client.post("/api/v1/orders", json=cqrs_create)
        assert response.status_code == 201
        assert "saga_id" in response.json()

        # REST: create order
        rest_response = await client.post("/rest/orders", json=test_order_data)
        assert rest_response.status_code == 201
        rest_order = rest_response.json()
        assert rest_order["order_id"] == order_id

        # CQRS: get order
        cqrs_get = await client.get(f"/api/v1/orders/{order_id}")
        assert cqrs_get.status_code == 200

        # REST: get order
        rest_get = await client.get(f"/rest/orders/{order_id}")
        assert rest_get.status_code == 200

        # GraphQL: get order
        graphql_query = """
        query GetOrderById($orderId: String!) {
            getOrderById(orderId: $orderId) {
                orderId
                userId
                amount
                status
            }
        }
        """
        graphql_variables = {"orderId": order_id}
        graphql_response = await client.post(
            "/graphql",
            json={"query": graphql_query, "variables": graphql_variables},
        )
        assert graphql_response.status_code == 200
        graphql_data = graphql_response.json()
        assert "data" in graphql_data
        assert graphql_data["data"]["getOrderById"]["orderId"] == order_id

        # REST: update order
        rest_update = await client.patch(
            f"/rest/orders/{order_id}",
            json={"status": "processing"},
        )
        assert rest_update.status_code == 200

        # GraphQL: update order
        graphql_update = """
        mutation UpdateOrder($orderId: String!, $orderUpdate: OrderUpdateInputGraphQL!) {
            updateOrder(orderId: $orderId, orderUpdate: $orderUpdate) {
                orderId
                status
            }
        }
        """
        graphql_update_variables = {
            "orderId": order_id,
            "orderUpdate": {"status": "completed"},
        }
        graphql_update_response = await client.post(
            "/graphql",
            json={"query": graphql_update, "variables": graphql_update_variables},
        )
        assert graphql_update_response.status_code == 200

        # CQRS: cancel order
        cqrs_cancel = await client.post(
            f"/api/v1/orders/{order_id}/cancel",
            json={"reason": "Test complete"},
        )
        assert cqrs_cancel.status_code == 200

        # REST: verify order still accessible
        rest_final = await client.get(f"/rest/orders/{order_id}")
        assert rest_final.status_code == 200
