请根据用户需求，从可用知识库列表中选择最合适的知识库。

用户需求：{rewritten_input}
工作流类型：{workflow_type}

可用知识库列表：
{knowledge_catalog}

匹配原则：
1. 语义匹配：选择与用户需求最相关的知识库
2. 领域匹配：优先选择同一领域的知识库（如政策、法律、科技等）
3. 权威性优先：优先选择官方、权威的知识库
4. 政策类查询：如果有多个政策相关知识库，可以都选中

请分析并返回：
- matched_knowledge_bases: 匹配的知识库列表（返回 id）
- retrieval_config: 检索配置（可选）
- reasoning: 匹配理由（50 字以内）

以 JSON 格式返回。
