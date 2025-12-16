"""
ASGI entrypoint so the backend can be served with uvicorn or hypercorn:

    uvicorn web.backend.main:app --reload
"""

from . import create_app

app = create_app()
