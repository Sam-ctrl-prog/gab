"""Entry point — starts the GAB server."""
import uvicorn
from backend.config import get_settings

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=s.app_host,
        port=s.app_port,
        reload=False,
    )
