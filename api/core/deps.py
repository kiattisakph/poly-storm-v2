from typing import Generator
from api.core.database import get_db


def db_conn() -> Generator:
    """
    FastAPI dependency สำหรับ inject DB connection เข้า route handler

    Usage:
        @router.get("/")
        def list_items(conn = Depends(db_conn)):
            ...
    """
    with get_db() as conn:
        yield conn