"""
CineMatch AI — Application entry point.

Run with:  python -m app
           uvicorn app.main:app --reload
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level,
        reload=True,
    )
