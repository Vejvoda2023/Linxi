1. **测试直播流转写**：
   您可以使用以下方式测试：

   ```bash
   curl -X POST "http://localhost:8001/api/transcribe/stream/" \
   -H "Content-Type: application/json" \
   -d '{
       "url": "您的直播流URL",
       "preferred_quality": "audio_only"
   }'
   ```

   或者使用 Python 请求：

   ```python
   import requests
   
   url = "http://localhost:8001/api/transcribe/stream/"
   data = {
       "url": "您的直播流URL",
       "preferred_quality": "audio_only"
   }
   
   response = requests.post(url, json=data)
   print(response.json())
   ```

2. **测试音频文件转写**：
   如果您想测试音频文件转写，可以使用：

   ```bash
   curl -X POST "http://localhost:8001/api/transcribe/" \
   -F "audio_file=@您的音频文件路径"
   ```

   或者使用 Python 请求：

   ```python
   import requests
   
   url = "http://localhost:8001/api/transcribe/"
   files = {
       "audio_file": open("您的音频文件路径", "rb")
   }
   
   response = requests.post(url, files=files)
   print(response.json())
   ```

3. **注意事项**：
   - 确保您的直播流URL是可访问的
   - 直播流格式应该是支持的音频格式（如 RTMP、HLS 等）
   - 转写结果会实时返回，您可以通过返回的 `task_id` 跟踪任务状态
   - 如果遇到错误，API 会返回相应的错误信息

4. **调试建议**：
   - 建议先用一个简单的音频文件测试，确保基本功能正常
   - 如果使用直播流，建议先用一个稳定的测试流进行测试
   - 观察服务器日志，查看是否有错误信息
   - 可以使用 FastAPI 的自动文档界面（访问 `http://localhost:8001/docs`）进行测试


