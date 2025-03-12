from aiohttp import web
from src.app import create_app

if __name__ == "__main__":
    print("Open http://localhost:8080/api/docs to see Swagger UI")  # noqa
    web_app = create_app()
    web.run_app(web_app, host="localhost", port=8080, print=None)
