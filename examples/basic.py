"""
Basic App
=========

Demonstrates use of the on_startup, on_shutdown events from the `ASGI Lifespan`.
And also added a '/' route (index page) which returns a JSON response.
"""

from allin import Allin, JSONResponse

app = Allin()


@app.on_startup
async def on_startup():
    print("lifespan on_startup event triggered!")


@app.on_shutdown
async def on_shutdown():
    print("lifespan on_shutdown event triggered!")


@app.route("/")
async def index():
    return JSONResponse({"message": "Hello World!"})
