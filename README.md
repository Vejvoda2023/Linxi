## 实时语音听写测试步骤

1. **启动流式转录**：
   
   - 请求类型：POST
   - URL：`http://localhost:8001/api/transcribe/stream/`
   - 请求体格式：JSON
   - 请求体内容：
     ```json
     {
       "url": "您的直播流URL",
       "preferred_quality": "audio_only"
     }
     ```
   - 说明：这个接口会返回一个task_id，您需要保存这个ID用于后续查询转录结果

2. **查询转录状态和结果**：
   
   - 请求类型：GET
   - URL：`http://localhost:8001/api/transcribe/status/{task_id}`
   - 说明：使用上一步返回的task_id替换{task_id}，这个接口会返回当前的转录状态和已转录的文本

3. **取消转录任务**（如果需要停止）：
   
   - 请求类型：DELETE
   - URL：`http://localhost:8001/api/transcribe/cancel/{task_id}`
   - 说明：使用task_id来取消正在进行的转录任务

## 实时翻译测试步骤

一旦获得了语音转录的文本，您可以使用以下接口进行文本翻译：

1. **常规文本翻译**：
   
   - 请求类型：POST
   - URL：`http://localhost:8001/api/translate/text`
   - 请求体格式：Form-data
   - 参数：
     - text：要翻译的文本（从转录接口获取）
     - source_lang：源语言代码（如"zh"表示中文）
     - target_lang：目标语言代码（如"en"表示英文）

2. **流式文本翻译**：
   
   - 请求类型：POST
   - URL：`http://localhost:8001/api/translate/stream`
   - 请求体格式：Form-data
   - 参数：
     - text：要翻译的文本（从转录接口获取）
     - source_lang：源语言代码
     - target_lang：目标语言代码
   - 说明：这个接口会以流的形式返回翻译结果，适合长文本翻译

## 完整测试流程

1. 调用`/api/transcribe/stream/`接口开始从直播流转录语音
2. 使用返回的task_id，定期调用`/api/transcribe/status/{task_id}`查询转录结果
3. 获取到转录文本后，使用`/api/translate/text`或`/api/translate/stream`接口进行翻译
4. 完成后，调用`/api/transcribe/cancel/{task_id}`取消转录任务

注意事项：
- 系统支持多种直播平台的URL，通过streamlink库处理
- 如果您有直接的音频流URL，可以设置`direct_url`参数为true
- 转录进程会在后台持续运行，直到您主动取消或发生错误
