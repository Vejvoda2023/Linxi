from fastapi import FastAPI
from app.api.endpoints.transcribe import router

app = FastAPI(title="Live Speech Transcription API")

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
