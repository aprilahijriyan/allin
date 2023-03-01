"""
Routing App
===========

Demonstrate use of:

* Example of Path parameters
* Include other routers to the App

On an Allin framework for route mapping we use the https://github.com/pyrates/autoroutes module.
So for path parameter specification, you can see the module documentation.
"""

from enum import Enum
from typing import Annotated, Optional
from uuid import UUID

from msgspec import Meta

from allin import Allin, JSONResponse, Router
from allin.globals import request


class Role(str, Enum):
    # NOTE: you cannot use dynamic enums (e.g. `Item(Enum)`).
    # You should add base classes like `str`, `int` to the Enum object like I did.
    admin = "admin"
    member = "member"
    influencer = "influencer"


app = Allin()


@app.get("/")
async def index():
    return JSONResponse({"message": "Hello world!"})


# If you visit localhost:8000/some-string it won't be found, because we're expecting a number as the path parameter.
# Try changing `some-string` to a number and you should see what you're expecting.
@app.get("/{id:digit}")
async def index_1(
    id,
):  # By default, the `id` argument is `str`. Try adding type-hint `int` to convert the value from string to integer.
    headers = request.headers
    # You must return a `Response` object in the endpoint function, otherwise Allin will throw an error.
    return JSONResponse({"id": id, "query": request.query(), "headers": headers})


@app.get("/readme/{uid}/{number}/{role}")
async def readme(
    uid: UUID,
    number: Annotated[
        int, Meta(gt=0, lt=10)
    ],  # There is an issue with `msgspec` (should work on version `>0.13.1`) (see: https://github.com/jcrist/msgspec/issues/334)
    role: Role,
):
    return JSONResponse({"uid": uid, "number": number, "role": role})


sub_router = Router(prefix="/sub")


@sub_router.get("/")
async def sub_router_index():
    return JSONResponse({"message": "Hello from the sub-router!"})


@sub_router.get("/{message}")
async def sub_router_index_custom_message(message: str):
    return JSONResponse({"message": message, "router": "sub"})


nested_router = Router(prefix="/nested")


@nested_router.get("/")
async def nested_router_index():
    return JSONResponse({"message": "Hello from nested-router!"})


@nested_router.get("/{message}")
async def nested_router_index_custom_message(message: str):
    return JSONResponse({"message": message, "router": "sub/nested"})


sub_router.include_router(nested_router)
app.include_router(sub_router)
