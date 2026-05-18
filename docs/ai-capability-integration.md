# AI Capability Integration Guide

Business contexts should call productized AI capabilities through `ai_service_api`.
Do not call LLM providers or `llm_runtime` directly from business code.

## Recommended Call Pattern

```python
from ai_service_api import AIExecuteOptions, get_ai_service

result = get_ai_service().execute(
    "sales.voice.analyze",
    {
        "audio": {
            "type": "audio",
            "name": audio.filename,
            "mime_type": audio.mime_type,
            "size": audio.size_bytes,
            "data_url": audio.data_url,
        },
        "filename": audio.filename,
        "brand": "Forevermark",
    },
    options=AIExecuteOptions(
        metadata={"voice_analysis_id": voice_analysis_id},
    ),
)
```

For audio, image, or video inputs, pass a full media variable object. A local business `file_id` is not enough for the model:

```json
{
  "type": "audio",
  "name": "call.mp3",
  "mime_type": "audio/mpeg",
  "size": 2263275,
  "data_url": "data:audio/mpeg;base64,..."
}
```

The capability prompt should explicitly reference the media variable:

```text
Audio file: {{filename}}
Brand: {{brand}}

{{audio}}

Return a single valid JSON object with this shape:
...
```

## Responsibilities

- Business contexts own orchestration: load files, build variables, call `AIService.execute`, parse outputs, and write business tables.
- AI capability contexts own prompt/runtime configuration, model routing, tenant overrides, and trace records.
- File contexts own upload, storage, preview, and download. Business contexts should keep only file references and load content only when executing an AI capability.
- Backend parsers should trust only allowlisted fields from AI output. Store raw AI responses separately for debugging.

## Avoid These Pitfalls

- Do not pass only `file_id` to an AI capability when the model needs file content. Load the file and pass `data_url` or a provider-accessible URL.
- Do not force `response_format={"type": "json_object"}` for multimodal Qwen Omni/SiliconFlow calls unless it has been verified with that exact model route. In this project it caused `messages are illegal: 151669 is not in list` for audio analysis. Prefer prompt-level JSON instructions and backend parsing.
- Do not send large business contract objects such as `output_contract` as runtime variables. Put the required output shape in the capability prompt.
- Do not use `developer_prompt` for SiliconFlow/Qwen-compatible routes. Some routes reject the `developer` role. Merge those instructions into `system_prompt` and keep `developer_prompt` empty.
- Do not assume updating a platform capability changes tenant behavior. A tenant-scoped capability with the same key overrides the platform capability.
- Do not mutate or seed AI capability rows at request runtime. Use explicit init scripts or admin configuration.

## Debug Checklist

1. Check `prompt_runtime_traces.input_variables_json` and confirm media variables include `type`, `mime_type`, and `data_url`.
2. Check `prompt_runtime_traces.rendered_messages_json` and confirm the user message contains a media content part.
3. Compare AI Studio success calls with business-context calls, especially `response_format`, `extra_body`, `model`, `temperature`, and variable shapes.
4. Check whether the tenant has a same-key capability override.
5. Check `llm_call_logs` for model route, provider, and provider-level error messages.
6. For failed background jobs, check both the business job table and the AI trace id/error stored in the job.

## Sales Voice Analysis Notes

`sales.voice.analyze` should receive:

- `audio`: full audio media variable object.
- `filename`: display filename for prompt context.
- `brand`: business brand context.

It should not receive:

- `file_id` as model input.
- `output_contract` or other large business-only schema objects.
- forced JSON mode via `AIExecuteOptions.response_format` unless the target model route has been verified to support it with audio input.
