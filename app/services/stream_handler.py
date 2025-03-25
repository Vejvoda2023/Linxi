import subprocess
import threading
import streamlink
import os


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

    def open_stream(self):
        """打开流并返回 ffmpeg 进程"""
        try:
            if not os.path.exists(FFMPEG_EXECUTABLE):
                raise FileNotFoundError(f"FFmpeg 未找到: {FFMPEG_EXECUTABLE}")

            if self.direct_url:
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
                    stderr=subprocess.DEVNULL,  # 避免打印错误信息
                )
                return self.ffmpeg_process

            # 使用 streamlink 获取音频流
            streams = streamlink.streams(self.url)
            if not streams:
                raise RuntimeError("未找到可用的流")

            quality = self.preferred_quality if self.preferred_quality in streams else "best"

            self.streamlink_process = subprocess.Popen(
                ['streamlink', self.url, quality, "-O"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # 避免打印错误信息
            )

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
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # 避免打印错误信息
            )

            # 创建线程传输数据
            threading.Thread(target=self._transfer_data, daemon=True).start()
            return self.ffmpeg_process

        except Exception as e:
            print(f"⚠️ 发生错误: {e}")
            self.close()
            return None

    def _transfer_data(self):
        """从 streamlink 传输数据到 ffmpeg"""
        try:
            while self.streamlink_process.poll() is None and self.ffmpeg_process.poll() is None:
                chunk = self.streamlink_process.stdout.read(1024)
                if chunk:
                    self.ffmpeg_process.stdin.write(chunk)
                    self.ffmpeg_process.stdin.flush()
        except Exception as e:
            print(f"⚠️ 传输数据时发生错误: {e}")
        finally:
            self.close()  # 发生错误时自动清理进程

    def close(self):
        """关闭进程"""
        try:
            if self.ffmpeg_process:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.stdout.close()
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()
                self.ffmpeg_process = None

            if self.streamlink_process:
                self.streamlink_process.stdout.close()
                self.streamlink_process.kill()
                self.streamlink_process.wait()
                self.streamlink_process = None

        except Exception as e:
            print(f"⚠️ 关闭进程时发生错误: {e}")
