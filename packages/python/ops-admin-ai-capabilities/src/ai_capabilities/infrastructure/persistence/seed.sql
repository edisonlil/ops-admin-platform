INSERT INTO ai_capabilities (
    tenant_id,
    capability_key,
    name,
    description,
    scope,
    binding_type,
    binding_key,
    call_method,
    system_prompt,
    developer_prompt,
    user_prompt_template,
    input_schema_json,
    output_schema_json,
    model_preferences_json,
    runtime_config_json,
    enabled
)
SELECT
    1,
    'prompt.polish',
    '提示词AI润色',
    '平台内置提示词辅助能力，用于润色和优化提示词内容。',
    'platform',
    'prompt_runtime',
    'prompt.polish',
    'aiService.execute',
    '你是一名资深提示词工程师，擅长将业务人员编写的提示词润色为结构清晰、约束明确、变量保留完整、可直接用于大模型调用的提示词。只输出润色后的提示词正文，不要解释修改过程。',
    '',
    '请润色下面的提示词，保留原始意图、业务事实、Markdown结构和所有 {{变量名}} 占位符。避免引入未提供的新业务规则。\n\n标题：{{title}}\n\n当前提示词：\n{{prompt}}',
    '{"type":"object","required":["prompt"],"properties":{"title":{"type":"string","label":"标题"},"prompt":{"type":"string","label":"当前提示词"}}}',
    '{"type":"text"}',
    '{"route_key":"default-chat"}',
    '{"output_format":"markdown"}',
    1
WHERE NOT EXISTS (
    SELECT 1
    FROM ai_capabilities
    WHERE tenant_id = 1 AND capability_key = 'prompt.polish' AND deleted = 0
);
