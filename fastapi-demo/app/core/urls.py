from fastapi import APIRouter
from strawberry.tools import merge_types
from strawberry import Schema
from strawberry.fastapi import GraphQLRouter

from ..order import REST as orderREST
from ..order import GraphQL as orderGraphQL


class MainRouter:
    def __init__(
        self,
        rest: APIRouter = APIRouter(),
        graphql: APIRouter = APIRouter(),
    ) -> None:
        self.rest = rest
        self.graphql = graphql


rest = APIRouter(prefix="/rest", tags=["REST"])
graphql = APIRouter(prefix="/graphql", tags=["GraphQL"])
main_router = MainRouter(rest=rest, graphql=graphql)


Query = merge_types("Query", (orderGraphQL.Query,))
Mutation = merge_types("Mutation", (orderGraphQL.Mutation,))
schema = Schema(query=Query, mutation=Mutation)

graphql_app = GraphQLRouter(
    schema=schema,
    path="/graphql",
    graphql_ide="graphiql"
)


app_routers = (orderREST.router,)

for router in app_routers:
    main_router.rest.include_router(router=router)

