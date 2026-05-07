import uvicorn
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    # Reload on .env changes too (default watch is mostly *.py).
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(_ROOT)],
        reload_includes=["*.py", ".env"],
    )
