import uvicorn

from marketpulse.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("marketpulse.api.app:app", host=settings.host, port=settings.port, reload=False)

