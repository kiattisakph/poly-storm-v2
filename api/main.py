from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import get_settings
from api.core.database import init_pool, get_pool
from api.routers import cities, trades, runs


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="STORM v2 API",
        version="2.0.0",
        docs_url="/docs" if settings.app_env != "production" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup():
        init_pool()

    @app.on_event("shutdown")
    def shutdown():
        get_pool().closeall()

    app.include_router(cities.router)
    app.include_router(trades.router)
    app.include_router(runs.router)

    @app.get("/health", tags=["system"])
    def health():
        try:
            conn = get_pool().getconn()
            conn.cursor().execute("SELECT 1")
            get_pool().putconn(conn)
            return {"status": "ok", "db": "connected"}
        except Exception as e:
            return {"status": "error", "db": str(e)}

    return app


app = create_app()