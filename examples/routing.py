"""
Routing App
===========

Demonstrate use of:

* Example of Path parameters
* Include other routers to the App

On an Allin framework for route mapping we use the https://github.com/pyrates/autoroutes module.
So for path parameter specification, you can see the module documentation.
"""

from allin import Allin, JSONResponse, Router
from allin.globals import request

app = Allin()

# If you visit localhost:8000/some-string it won't be found, because we're expecting a number as the path parameter.
# Try changing `some-string` to a number and you should see what you're expecting.
@app.get("/{id:digit}")
async def index(id: int):
    # You must return a `Response` object in the endpoint function, otherwise Allin will throw an error.
    headers = request.headers
    return JSONResponse({"id": id, "query": request.query(), "headers": headers})


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
