# allin

<p align="center">
Allin is an experimental asynchronous web framework.
</p>
<p align="center">
<img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/allin?color=yellow&logo=python&style=for-the-badge">
<img alt="PyPI" src="https://img.shields.io/pypi/v/allin?logo=python&style=for-the-badge">
<img alt="PyPI - Status" src="https://img.shields.io/pypi/status/allin?color=red&logo=python&style=for-the-badge">
</p>
<p align="center">
<strong>I didn't expect this framework to be used in a production environment, as it's still in the early stages of development.</strong>
Not sure when this framework can be used in production 😬
</p>

> You can help this project get better by creating an [issue](https://github.com/aprilahijriyan/allin/issues) or PR. Thank you for your time!

Table of Contents:

* [:raised_eyebrow: Why ?](#🤨-why)
* [:books: Roadmap](#📚-roadmap)
* [:star_struck: Features](#🤩-features)
* [:love_you_gesture: Quick Start](#🤟-quick-start)
* [:sunglasses: Installation](#😎-installation)

    * [From source](#install-from-source)
    * [With `pip`](#install-with-pip)

`Allin` is heavily inspired by [Flask](https://flask.palletsprojects.com/en/2.2.x/), [Starlette](https://www.starlette.io/) & [Falcon](https://falconframework.org/).

## :raised_eyebrow: Why ?

> I'm just curious :monocle_face:

[ASGI]: https://asgi.readthedocs.io/en/latest

Yup, I'm curious about how a web application based on [ASGI] works.

It may not yet fully comply with the [ASGI] application specifications as documented. But, for the main features like route mapping, HTTP responses, error handling, parsing the request body it's there.

...and I want to build my own framework from scratch so I know how the application works.

Literally, the "framework parts" weren't built from scratch as I also used third party modules and some "parts from other sources" were used as references.

> _This is part of the journey_

## :books: Roadmap

- [x] Lifespan Protocol
- [x] HTTP Protocol

    - [x] HTTP Headers
    - [x] HTTP Request
        - [x] JSON Body Support
        - [x] MessagePack Body Support
        - [x] Form Data Support
        - [x] Cookies
        - [x] Query Parameters

    - [x] HTTP Responses
        - [x] JSONResponse
        - [x] MessagePackResponse

    - [ ] HTTP Middleware
        - [ ] Before HTTP Request
        - [ ] After HTTP Request

    - [x] Routing

        - [x] Decorator shortcuts such as `@get`, `@post`, `@put`, etc. are available.
        - [x] Nesting routers

- [ ] Extension
- [ ] Websocket Support

## :star_struck: Features

- [x] Global variables. (It means, you can access the `app` and `request` object instances globally)
- [x] Error handling
- [x] `JSON` and `MessagePack` requests are supported out of the box (thanks to [msgspec](https://github.com/jcrist/msgspec))
- [x] Form Data Support (`application/x-www-form-urlencoded` or `multipart/form-data`)
- [x] Decorator shortcuts such as `@get`, `@post`, `@put`, etc. are available.
- [x] Nesting routers

## :love_you_gesture: Quick Start

Here is an example application based on the `Allin` framework and I'm sure you are familiar with it.

```python
from allin import Allin, JSONResponse

app = Allin()

@app.route("/")
async def index():
    return JSONResponse({"message": "Hello World!"})
```

<details>
<summary>:point_down: Explanation</summary>

* The `app` variable is the ASGI application instance.
* And we create an endpoint with the route `/` on the line `app.route(...)`
* Then we add the `index()` function to handle the `/` route.
* And the handler function will return a JSON response with the content `{"message": "Hello World!"}`

</details>

That's it! looks familiar right?

Want more? check out other [sample projects here](https://github.com/aprilahijriyan/allin/tree/main/examples)

## :sunglasses: Installation

### Install from source

```
git clone --depth 1 https://github.com/aprilahijriyan/allin.git
cd allin
```

Need https://python-poetry.org/ installed on your device

```
poetry build
pip install ./dist/*.whl
```

### Install with `pip`

Currently I just published the pre-release version `v0.1.1a0`. So, maybe you need to install it with the `--pre` option. Example:

```
pip install --pre allin
```
