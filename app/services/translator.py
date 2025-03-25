import httpx
import json
import logging
import time
import os
from typing import AsyncGenerator, Union
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential
from asyncio import Semaphore
from app.utils.language import LANGUAGE_MAPPING

logger = logging.getLogger(__name__)


class DeepSeekTranslator:
    def __init__(self, max_concurrent: int = 10):
        self.api_url = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        
        if not all([self.api_url, self.api_key, self.model]):
            raise RuntimeError("DeepSeek配置不完整，请检查环境变量")

        self._client = httpx.AsyncClient()
        self._semaphore = Semaphore(max_concurrent)

    @property
    def api_url(self) -> str:
        return self._api_url
        
    @api_url.setter
    def api_url(self, value: str):
        self._api_url = value

    @property
    def api_key(self) -> str:
        return self._api_key
        
    @api_key.setter
    def api_key(self, value: str):
        self._api_key = value

    @property
    def model(self) -> str:
        return self._model
        
    @model.setter
    def model(self, value: str):
        self._model = value

    async def translate(
            self,
            text: str,
            source_lang: str,
            target_lang: str,
            stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """翻译核心方法"""
        if not self._validate_language(source_lang, target_lang):
            raise ValueError("不支持的语言代码")

        headers = self._build_headers()
        data = self._build_request_data(text, source_lang, target_lang, stream)

        if stream:
            return self._stream_translate(headers, data)
        else:
            return await self._normal_translate(headers, data)

    def _validate_language(self, source_lang: str, target_lang: str) -> bool:
        """验证语言代码"""
        return all(lang in LANGUAGE_MAPPING for lang in [source_lang, target_lang])

    def _build_headers(self) -> dict:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @lru_cache(maxsize=1024)
    def _build_prompt(self, text: str, source_lang: str, target_lang: str, stream: bool) -> str:
        """构建翻译提示词(带缓存)"""
        prompt_template = """
        你是一个专业的翻译助手，请将以下 {source} 文本翻译成 {target}。
        保持原意不变，但可以根据目标语言的表达习惯适当调整语序和用词。
        {extra}

        原文: {text}
        """
        return prompt_template.format(
            source=LANGUAGE_MAPPING[source_lang],
            target=LANGUAGE_MAPPING[target_lang],
            text=text,
            extra="请逐句翻译并立即返回结果，不要等待全文。" if stream else "只返回翻译结果，不要添加任何解释或额外内容。"
        )

    def _build_request_data(self, text: str, source_lang: str, target_lang: str, stream: bool) -> dict:
        """构建请求数据"""
        return {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": self._build_prompt(text, source_lang, target_lang, stream)
            }],
            "temperature": 0.3,
            "max_tokens": 2000,
            "stream": stream
        }

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _normal_translate(self, headers: dict, data: dict) -> str:
        """普通翻译模式(带重试机制)"""
        start = time.monotonic()
        async with self._semaphore:
            try:
                response = await self._client.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            except httpx.HTTPStatusError as e:
                logger.error(f"DeepSeek API请求失败: {e.response.text}")
                raise RuntimeError("翻译服务暂时不可用")
            except httpx.RequestError as e:
                logger.error(f"网络错误: {e}")
                raise RuntimeError("无法连接翻译服务")
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"DeepSeek API返回格式异常: {e}")
                raise RuntimeError("翻译服务返回了无效的数据")
            finally:
                logger.info(f"翻译耗时: {time.monotonic() - start:.2f}s")

    async def _stream_translate(self, headers: dict, data: dict) -> AsyncGenerator[str, None]:
        """流式翻译模式"""
        async with self._semaphore:
            try:
                async with self._client.stream(
                        "POST",
                        self.api_url,
                        headers=headers,
                        json=data,
                        timeout=30.0
                ) as response:
                    response.raise_for_status()

                    async for chunk in response.aiter_lines():
                        if chunk.startswith("data: ") and (chunk := chunk[6:].strip()) not in ("", "[DONE]"):
                            try:
                                if content := json.loads(chunk).get("choices", [{}])[0].get("delta", {}).get("content"):
                                    yield content
                            except json.JSONDecodeError:
                                continue
            except httpx.HTTPStatusError as e:
                logger.error(f"DeepSeek API流式请求失败: {e.response.text}")
                raise RuntimeError("翻译服务暂时不可用")
            except httpx.RequestError as e:
                logger.error(f"网络错误: {e}")
                raise RuntimeError("无法连接翻译服务")

    async def close(self):
        """释放资源"""
        await self._client.aclose()


# 单例
translator = DeepSeekTranslator()