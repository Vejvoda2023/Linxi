import subprocess
import threading
import streamlink
import os
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


FFMPEG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../bin/ffmpeg/bin"))
FFMPEG_EXECUTABLE = os.path.join(FFMPEG_PATH, "ffmpeg.exe")


class StreamHandler:
    def __init__(self, url, preferred_quality="audio_only", direct_url=False):
        self.url = url
        self.preferred_quality = preferred_quality
        self.direct_url = direct_url
        self.ffmpeg_process = None
        self.streamlink_process = None
        self._transfer_thread = None
        self._stopping = False

    def open_stream(self):
        """打开流并返回 ffmpeg 进程"""
        if self.ffmpeg_process is not None:
            logger.warning("Stream handler already has a running process. Closing it first.")
            self.close()
            
        self._stopping = False
        
        try:
            if not os.path.exists(FFMPEG_EXECUTABLE):
                logger.error(f"FFmpeg 未找到: {FFMPEG_EXECUTABLE}")
                raise FileNotFoundError(f"FFmpeg 未找到: {FFMPEG_EXECUTABLE}")

            if self.direct_url:
                logger.info(f"使用直接URL打开流: {self.url}")
                self.ffmpeg_process = subprocess.Popen(
                    [
                        FFMPEG_EXECUTABLE,
                        "-i", self.url,
                        "-loglevel", "panic",
                        "-f", "s16le",
                        "-acodec", "pcm_s16le",
                        "-ac", "1",
                        "-ar", str(SAMPLE_RATE),
                        "-"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,  # 捕获错误以便日志记录
                )
                
                # 检查进程是否立即终止
                time.sleep(0.5)
                if self.ffmpeg_process.poll() is not None:
                    stderr = self.ffmpeg_process.stderr.read().decode('utf-8', errors='ignore')
                    logger.error(f"FFmpeg进程启动失败: {stderr}")
                    raise RuntimeError(f"FFmpeg无法处理直接URL: {stderr}")
                
                return self.ffmpeg_process

            # 使用 streamlink 获取音频流
            logger.info(f"使用streamlink获取流: {self.url}")
            try:
                streams = streamlink.streams(self.url)
                if not streams:
                    logger.error(f"未找到可用的流: {self.url}")
                    raise RuntimeError(f"未找到可用的流: {self.url}")
                
                quality = self.preferred_quality if self.preferred_quality in streams else "best"
                logger.info(f"使用质量: {quality}")
                
                self.streamlink_process = subprocess.Popen(
                    ['streamlink', self.url, quality, "-O"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,  # 捕获错误以便日志记录
                )
                
                # 检查streamlink进程是否立即终止
                time.sleep(0.5)
                if self.streamlink_process.poll() is not None:
                    stderr = self.streamlink_process.stderr.read().decode('utf-8', errors='ignore')
                    logger.error(f"Streamlink进程启动失败: {stderr}")
                    raise RuntimeError(f"Streamlink无法获取流: {stderr}")
                
            except Exception as e:
                logger.error(f"Streamlink错误: {e}")
                self.close()
                raise

            try:
                self.ffmpeg_process = subprocess.Popen(
                    [
                        FFMPEG_EXECUTABLE,
                        "-i", "-",
                        "-loglevel", "panic",
                        "-f", "s16le",
                        "-acodec", "pcm_s16le",
                        "-ac", "1",
                        "-ar", str(SAMPLE_RATE),
                        "-"
                    ],
                    stdin=self.streamlink_process.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,  # 捕获错误以便日志记录
                )
                
                # 检查FFmpeg进程是否立即终止
                time.sleep(0.5)
                if self.ffmpeg_process.poll() is not None:
                    stderr = self.ffmpeg_process.stderr.read().decode('utf-8', errors='ignore')
                    logger.error(f"FFmpeg进程启动失败: {stderr}")
                    raise RuntimeError(f"FFmpeg处理错误: {stderr}")
                
                # 关闭不需要的文件描述符
                self.streamlink_process.stdout.close()
                
                logger.info("成功打开流处理管道")
                return self.ffmpeg_process
                
            except Exception as e:
                logger.error(f"FFmpeg错误: {e}")
                self.close()
                raise

        except Exception as e:
            logger.error(f"⚠️ 打开流时发生错误: {e}")
            self.close()
            raise

    def close(self):
        """关闭进程"""
        self._stopping = True
        
        try:
            # 按照依赖顺序关闭
            if self.ffmpeg_process:
                logger.info("关闭FFmpeg进程")
                try:
                    if hasattr(self.ffmpeg_process, 'stdin') and self.ffmpeg_process.stdin:
                        self.ffmpeg_process.stdin.close()
                except:
                    pass
                    
                try:
                    if hasattr(self.ffmpeg_process, 'stdout') and self.ffmpeg_process.stdout:
                        self.ffmpeg_process.stdout.close()
                except:
                    pass
                    
                try:
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait(timeout=2)
                except:
                    try:
                        self.ffmpeg_process.kill()
                        self.ffmpeg_process.wait(timeout=2)
                    except:
                        pass
                        
                self.ffmpeg_process = None

            if self.streamlink_process:
                logger.info("关闭Streamlink进程")
                try:
                    if hasattr(self.streamlink_process, 'stdout') and self.streamlink_process.stdout:
                        self.streamlink_process.stdout.close()
                except:
                    pass
                    
                try:
                    self.streamlink_process.terminate()
                    self.streamlink_process.wait(timeout=2)
                except:
                    try:
                        self.streamlink_process.kill()
                        self.streamlink_process.wait(timeout=2)
                    except:
                        pass
                        
                self.streamlink_process = None

        except Exception as e:
            logger.error(f"⚠️ 关闭进程时发生错误: {e}")
            
    def __enter__(self):
        """上下文管理器支持"""
        self.open_stream()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器支持"""
        self.close()
