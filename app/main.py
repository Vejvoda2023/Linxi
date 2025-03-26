from fastapi import FastAPI
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

from app.api.endpoints.transcribe import router as transcribe_router
from app.api.endpoints.translate import router as translate_router

app = FastAPI(title="Live Speech Transcription API")

app.include_router(transcribe_router, prefix="/api")
app.include_router(translate_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
