from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.transcriber import Transcriber, TimestampedText
from app.services.stream_handler import StreamHandler
from pydantic import BaseModel
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional

router = APIRouter()
transcriber = Transcriber()
# 用于存储和跟踪活动任务
active_tasks: Dict[str, Dict[str, Any]] = {}
logger = logging.getLogger(__name__)


class StreamURL(BaseModel):
    url: str
    preferred_quality: str = "audio_only"


class TimestampedResponse(BaseModel):
    text: str
    start_time: float
    end_time: float


class TranscriptionResponse(BaseModel):
    transcription: str
    timestamps: Optional[List[TimestampedResponse]] = None


@router.post("/transcribe/", response_model=TranscriptionResponse)
async def transcribe(audio_file: UploadFile = File(...), include_timestamps: bool = False):
    """上传音频文件并进行语音识别
    Args:
        audio_file: 音频文件
        include_timestamps: 是否包含时间戳信息
    """
    try:
        audio_data = await audio_file.read()

        transcriber.connect()
        transcriber.send(audio_data)
        transcriber.send_end_tag()

        result = transcriber.get_transcription(include_timestamps=include_timestamps)
        if include_timestamps:
            return TranscriptionResponse(
                transcription="".join(item.text for item in result),
                timestamps=[TimestampedResponse(
                    text=item.text,
                    start_time=item.start_time,
                    end_time=item.end_time
                ) for item in result]
            )
        return TranscriptionResponse(transcription=result)
    except Exception as e:
        logger.error(f"转录处理错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"转录处理错误: {str(e)}")
    finally:
        transcriber.close()


@router.post("/transcribe/stream/")
async def transcribe_stream(stream_data: StreamURL, include_timestamps: bool = False):
    """处理直播流并进行实时语音识别
    Args:
        stream_data: 流媒体URL信息
        include_timestamps: 是否包含时间戳信息
    """
    try:
        stream_handler = StreamHandler(
            url=stream_data.url,
            preferred_quality=stream_data.preferred_quality
        )
        transcriber.connect()
        process = stream_handler.open_stream()
        
        if not process:
            raise HTTPException(status_code=500, detail="无法打开流")

        # 生成唯一任务ID
        task_id = str(uuid.uuid4())

        async def process_stream():
            try:
                while True:
                    # 避免阻塞
                    in_bytes = await asyncio.to_thread(process.stdout.read1, 4096)
                    if not in_bytes:
                        break

                    transcriber.send(in_bytes)

                    # 更新任务状态和当前文本
                    result = transcriber.get_transcription(include_timestamps=include_timestamps)
                    if include_timestamps:
                        active_tasks[task_id]["current_text"] = "".join(item.text for item in result)
                        active_tasks[task_id]["timestamps"] = [
                            {
                                "text": item.text,
                                "start_time": item.start_time,
                                "end_time": item.end_time
                            } for item in result
                        ]
                    else:
                        active_tasks[task_id]["current_text"] = result
                    
            except Exception as e:
                logger.error(f"流处理错误: {str(e)}")
                active_tasks[task_id]["error"] = str(e)
            finally:
                # 确保资源清理
                stream_handler.close()
                transcriber.close()
                active_tasks[task_id]["status"] = "completed"

        # 创建并存储任务
        task = asyncio.create_task(process_stream())
        active_tasks[task_id] = {
            "task": task,
            "status": "running",
            "current_text": "",
            "timestamps": [] if include_timestamps else None,
            "error": None
        }

        return {
            "message": "Stream processing started", 
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"启动流处理错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transcribe/status/{task_id}", response_model=TranscriptionResponse)
async def get_transcription_status(task_id: str):
    """获取流转录任务的状态和结果"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = active_tasks[task_id]
    
    return TranscriptionResponse(
        transcription=task_info["current_text"],
        timestamps=task_info.get("timestamps")
    )


@router.delete("/transcribe/cancel/{task_id}")
async def cancel_transcription(task_id: str):
    """取消正在进行的转录任务"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = active_tasks[task_id]
    
    if task_info["status"] == "running":
        task_info["task"].cancel()
        task_info["status"] = "cancelled"
        
        # 清理资源
        transcriber.close()
        
    return {"message": f"任务 {task_id} 已取消"}
