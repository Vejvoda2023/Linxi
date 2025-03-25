from fastapi import APIRouter, HTTPException, Form, UploadFile
from fastapi.responses import StreamingResponse
from app.services.translator import translator
from app.utils.language import LANGUAGE_MAPPING
from typing import Optional
import logging

router = APIRouter(prefix="/translate", tags=["translation"])
logger = logging.getLogger(__name__)

@router.post("/text")
async def translate_text(
    text: str = Form(..., description="要翻译的文本"),
    source_lang: str = Form(..., description="源语言代码，如 'zh', 'en'"),
    target_lang: str = Form(..., description="目标语言代码，如 'en', 'zh'")
):
    """
    文本翻译接口
    """
    try:
        translated_text = await translator.translate(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            stream=False
        )
        return {"translated_text": translated_text}
    except ValueError as e:
        logger.error(f"源语言或目标语言无效: {e}")
        raise HTTPException(status_code=400, detail=f"无效的语言代码: {e}")
    except Exception as e:
        logger.error(f"翻译失败, text={text}, source_lang={source_lang}, target_lang={target_lang}, error={e}")
        raise HTTPException(status_code=500, detail="翻译服务暂时不可用")

@router.post("/stream")
async def translate_text_stream(
    text: str = Form(..., description="要翻译的文本"),
    source_lang: str = Form(..., description="源语言代码，如 'zh', 'en'"),
    target_lang: str = Form(..., description="目标语言代码，如 'en', 'zh'")
):
    """
    流式文本翻译接口
    """
    try:
        return StreamingResponse(
            translator.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                stream=True
            ),
            media_type="text/event-stream"
        )
    except ValueError as e:
        logger.error(f"源语言或目标语言无效: {e}")
        raise HTTPException(status_code=400, detail=f"无效的语言代码: {e}")
    except Exception as e:
        logger.error(f"流式翻译失败, text={text}, source_lang={source_lang}, target_lang={target_lang}, error={e}")
        raise HTTPException(status_code=500, detail="翻译服务暂时不可用")

@router.post("/audio")
async def translate_audio(
    audio_file: UploadFile,
    source_lang: str = Form(..., description="源语言代码"),
    target_lang: str = Form(..., description="目标语言代码")
):
    """
    音频翻译接口 (需要先调用transcribe接口获取文本)
    """
    try:
        # 在实际应用中，这里应该调用你的transcribe服务
        # 这里简化处理，直接返回提示
        raise HTTPException(
            status_code=501,
            detail="请先调用/transcribe接口获取文本，再调用翻译接口"
        )
    except Exception as e:
        logger.error(f"音频翻译失败, error={e}")
        raise HTTPException(status_code=500, detail=f"音频翻译失败: {e}")
