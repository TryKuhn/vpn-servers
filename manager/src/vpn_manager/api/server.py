"""Entry point for the HTTP server.

Run with:
    python -m vpn_manager.api.server

Or directly via uvicorn (used in production):
    uvicorn vpn_manager.api.server:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

from vpn_manager.api.app import create_app
from vpn_manager.config import Settings
from vpn_manager.storage.users_store import UsersStore


def _build() -> object:
    """Construct the FastAPI app with production dependencies."""
    settings = Settings.from_env()
    store = UsersStore(settings.users_db_path)
    return create_app(settings, store)


# Top-level `app` is what uvicorn imports.
app = _build()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "vpn_manager.api.server:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )
