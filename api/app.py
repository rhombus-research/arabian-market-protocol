from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as rest_router
from api.ws import router as ws_router


def create_app() -> FastAPI:
    app = FastAPI(title="Arabian Market Protocol", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5200", "http://127.0.0.1:5200"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(rest_router)
    app.include_router(ws_router)

    return app


app = create_app()
