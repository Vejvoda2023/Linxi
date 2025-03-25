from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.transcriber import Transcriber
from app.services.stream_handler import StreamHandler
from pydantic import BaseModel
import asyncio

router = APIRouter()
transcriber = Transcriber()


class StreamURL(BaseModel):
    url: str
    preferred_quality: str = "audio_only"


@router.post("/transcribe/")
async def transcribe(audio_file: UploadFile = File(...)):
    """上传音频文件并进行语音识别"""
    audio_data = await audio_file.read()

    transcriber.connect()
    transcriber.send(audio_data)
    transcriber.send_end_tag()

    return {"transcription": transcriber.get_transcription()}


@router.post("/transcribe/stream/")
async def transcribe_stream(stream_data: StreamURL):
    """处理直播流并进行实时语音识别"""
    try:
        stream_handler = StreamHandler(
            url=stream_data.url,
            preferred_quality=stream_data.preferred_quality
        )
        transcriber.connect()
        process = stream_handler.open_stream()

        async def process_stream():
            try:
                while True:
                    #改进：避免阻塞
                    in_bytes = await asyncio.to_thread(process.stdout.read1, 4096)
                    if not in_bytes:
                        break

                    transcriber.send(in_bytes)

                    #如果需要 WebSocket 实时推送结果，可以在这里加
                    current_text = transcriber.get_transcription()

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"流处理错误: {str(e)}")
            finally:
                #确保资源清理
                stream_handler.close()
                transcriber.close()

        #改进：返回 task，让调用方可以管理
        task = asyncio.create_task(process_stream())

        return {"message": "Stream processing started", "task_id": id(task)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
