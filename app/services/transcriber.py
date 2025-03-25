import os
import time
import json
import logging
import threading
import base64
import hmac
import hashlib
from websocket import create_connection, WebSocketConnectionClosedException
from urllib.parse import quote
from contextlib import contextmanager
from threading import Lock

logger = logging.getLogger(__name__)

class WebsocketError(Exception):
    """WebSocket错误"""
    pass


class Transcriber:
    def __init__(self):
        self.app_id = os.getenv('APP_ID')
        self.api_key = os.getenv('API_KEY')
        self.base_url = "ws://rtasr.xfyun.cn/v1/ws"
        self.end_tag = json.dumps({"end": True})
        self.ws = None
        self.is_connected = False
        self.recv_thread = None
        self.result_text = ""
        self._lock = Lock()  # 添加锁以保护并发访问

    def _generate_signature(self) -> tuple:
        """生成 WebSocket 连接所需的签名"""
        ts = str(int(time.time()))
        md5 = hashlib.md5((self.app_id + ts).encode('utf-8')).hexdigest().encode('utf-8')
        signa = base64.b64encode(hmac.new(self.api_key.encode('utf-8'), md5, hashlib.sha1).digest()).decode('utf-8')
        return ts, signa

    def connect(self):
        """建立 WebSocket 连接"""
        with self._lock:
            if self.is_connected:
                return

            # 先清理之前可能存在的连接
            self._cleanup_connection()

            try:
                ts, signa = self._generate_signature()
                ws_url = f"{self.base_url}?appid={self.app_id}&ts={ts}&signa={quote(signa)}"
                self.ws = create_connection(ws_url)
                self.is_connected = True

                self.recv_thread = threading.Thread(target=self.recv)
                self.recv_thread.daemon = True  # 设置为守护线程
                self.recv_thread.start()

                logger.info("WebSocket连接建立成功")
            except Exception as e:
                self.is_connected = False
                self.ws = None
                logger.error(f"WebSocket连接失败: {str(e)}")
                raise WebsocketError(f"WebSocket连接失败: {str(e)}")

    def _cleanup_connection(self):
        """清理已有连接"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
        self.is_connected = False

    def send(self, audio_data: bytes):
        """发送音频数据"""
        if not self.is_connected or not self.ws:
            try:
                self.connect()
            except WebsocketError as e:
                logger.error(f"发送时无法连接WebSocket: {str(e)}")
                raise

        chunk_size = 1280
        try:
            for i in range(0, len(audio_data), chunk_size):
                with self._lock:
                    if not self.is_connected:
                        raise WebsocketError("WebSocket连接已断开")

                    chunk = audio_data[i:i + chunk_size]
                    self.ws.send(chunk)
                    time.sleep(0.04)  # 控制发送速率
        except WebSocketConnectionClosedException:
            # 尝试重连
            logger.warning("发送时WebSocket连接断开，尝试重连")
            self.connect()
            # 重新发送这个数据包
            self.send(audio_data)
        except Exception as e:
            logger.error(f"发送音频数据时出错: {str(e)}")
            raise WebsocketError(f"发送音频数据时出错: {str(e)}")

    def send_end_tag(self):
        """发送结束标记"""
        with self._lock:
            if self.is_connected and self.ws:
                try:
                    self.ws.send(self.end_tag.encode('utf-8'))
                    logger.info("结束标记发送成功")
                except Exception as e:
                    logger.error(f"发送结束标记时出错: {str(e)}")
                    raise WebsocketError(f"发送结束标记时出错: {str(e)}")

    def recv(self):
        """接收识别结果"""
        try:
            while self.is_connected and self.ws:
                try:
                    result = self.ws.recv()
                    if not result:
                        logger.info("接收结果结束")
                        break

                    result_dict = json.loads(result)
                    self._handle_result(result_dict)
                except WebSocketConnectionClosedException:
                    logger.warning("WebSocket连接已关闭")
                    break
                except json.JSONDecodeError:
                    logger.warning("接收到无效的JSON数据")
                    continue
                except Exception as e:
                    logger.error(f"接收数据时出错: {str(e)}")
                    break

        except Exception as e:
            logger.error(f"接收线程出错: {str(e)}")
        finally:
            with self._lock:
                self.is_connected = False

    def _handle_result(self, result_dict: dict):
        """处理识别结果"""
        if result_dict.get("action") == "result":
            try:
                data = json.loads(result_dict["data"])
                words = []
                for rt in data['cn']['st']['rt']:
                    for ws in rt['ws']:
                        for cw in ws['cw']:
                            words.append(cw['w'])
                word = ''.join(words)
                with self._lock:
                    self.result_text += word
                logger.info(f"识别结果: {word}")
            except Exception as e:
                logger.error(f"解析识别结果时出错: {str(e)}")

    def close(self):
        """关闭连接"""
        with self._lock:
            if self.ws:
                try:
                    self.send_end_tag()
                except:
                    pass
                try:
                    self.ws.close()
                except:
                    pass
            self.ws = None
            self.is_connected = False
            logger.info("连接已关闭")

    def get_transcription(self):
        """获取识别文本"""
        with self._lock:
            return self.result_text

    def __enter__(self):
        """上下文管理器支持"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器支持"""
        self.close()
