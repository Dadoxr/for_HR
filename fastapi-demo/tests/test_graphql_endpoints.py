from tests.conftest import client, test_order_data


class TestGraphQLEndpoints:
    def test_graphql_get_all_orders_query(self, client):
        query = """
        query {
            getAllOrders {
                orderId
                userId
                amount
                status
            }
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "getAllOrders" in data["data"]
        assert isinstance(data["data"]["getAllOrders"], list)

    def test_graphql_create_order_mutation(self, client, test_order_data):
        mutation = """
        mutation CreateOrder($order: OrderCreateInputGraphQL!) {
            createOrder(order: $order) {
                orderId
                userId
                amount
                status
            }
        }
        """
        variables = {
            "order": {
                "orderId": test_order_data["order_id"],
                "userId": test_order_data["user_id"],
                "amount": test_order_data["amount"]
            }
        }
        response = client.post(
            "/graphql",
            json={"query": mutation, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "createOrder" in data["data"]
        order = data["data"]["createOrder"]
        assert order["orderId"] == test_order_data["order_id"]
        assert order["userId"] == test_order_data["user_id"]
        assert order["status"] == "pending"

    def test_graphql_get_order_by_id_query(self, client, test_order_data):
        mutation = """
        mutation CreateOrder($order: OrderCreateInputGraphQL!) {
            createOrder(order: $order) {
                orderId
            }
        }
        """
        variables = {
            "order": {
                "orderId": test_order_data["order_id"],
                "userId": test_order_data["user_id"],
                "amount": test_order_data["amount"]
            }
        }
        client.post("/graphql", json={"query": mutation, "variables": variables})

        # Query order
        query = """
        query GetOrderById($orderId: String!) {
            getOrderById(orderId: $orderId) {
                orderId
                userId
                amount
                status
            }
        }
        """
        variables = {"orderId": test_order_data["order_id"]}
        response = client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "getOrderById" in data["data"]
        order = data["data"]["getOrderById"]
        assert order["orderId"] == test_order_data["order_id"]

    def test_graphql_get_orders_by_user_id_query(self, client, test_order_data):
        mutation = """
        mutation CreateOrder($order: OrderCreateInputGraphQL!) {
            createOrder(order: $order) {
                orderId
            }
        }
        """
        variables = {
            "order": {
                "orderId": test_order_data["order_id"],
                "userId": test_order_data["user_id"],
                "amount": test_order_data["amount"]
            }
        }
        client.post("/graphql", json={"query": mutation, "variables": variables})
        query = """
        query GetOrdersByUserId($userId: String!) {
            getOrdersByUserId(userId: $userId) {
                orderId
                userId
                amount
                status
            }
        }
        """
        variables = {"userId": test_order_data["user_id"]}
        response = client.post(
            "/graphql",
            json={"query": query, "variables": variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "getOrdersByUserId" in data["data"]
        orders = data["data"]["getOrdersByUserId"]
        assert isinstance(orders, list)
        assert len(orders) > 0

    def test_graphql_update_order_mutation(self, client, test_order_data):
        create_mutation = """
        mutation CreateOrder($order: OrderCreateInputGraphQL!) {
            createOrder(order: $order) {
                orderId
            }
        }
        """
        create_variables = {
            "order": {
                "orderId": test_order_data["order_id"],
                "userId": test_order_data["user_id"],
                "amount": test_order_data["amount"]
            }
        }
        client.post("/graphql", json={"query": create_mutation, "variables": create_variables})
        update_mutation = """
        mutation UpdateOrder($orderId: String!, $orderUpdate: OrderUpdateInputGraphQL!) {
            updateOrder(orderId: $orderId, orderUpdate: $orderUpdate) {
                orderId
                status
            }
        }
        """
        update_variables = {
            "orderId": test_order_data["order_id"],
            "orderUpdate": {"status": "completed"}
        }
        response = client.post(
            "/graphql",
            json={"query": update_mutation, "variables": update_variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "updateOrder" in data["data"]
        order = data["data"]["updateOrder"]
        assert order["status"] == "completed"

    def test_graphql_delete_order_mutation(self, client, test_order_data):
        create_mutation = """
        mutation CreateOrder($order: OrderCreateInputGraphQL!) {
            createOrder(order: $order) {
                orderId
            }
        }
        """
        create_variables = {
            "order": {
                "orderId": test_order_data["order_id"],
                "userId": test_order_data["user_id"],
                "amount": test_order_data["amount"]
            }
        }
        client.post("/graphql", json={"query": create_mutation, "variables": create_variables})
        delete_mutation = """
        mutation DeleteOrder($orderId: String!) {
            deleteOrder(orderId: $orderId)
        }
        """
        delete_variables = {"orderId": test_order_data["order_id"]}
        response = client.post(
            "/graphql",
            json={"query": delete_mutation, "variables": delete_variables}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["deleteOrder"] is None

