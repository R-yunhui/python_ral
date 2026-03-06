本任务：根据下方上下文**创建一个毕昇(Bisheng)平台的工作流**，输出符合 bisheng-workflow-generator 规范的 JSON，并做自检迭代。

【用户需求分析】
{user_analysis}

【候选资源（按需选用，不必全部使用）】

候选工具（tool_key 必须原样写入 JSON，与需求不直接相关的请忽略）：
{tools_info}

候选知识库（仅当需求涉及文档检索时使用）：
{knowledge_info}

【工作流设计原则】
1. 保守优先：用户未明确要求的能力不要添加；简单场景工作流应精简
2. 工具/知识库按需选用，与需求不直接相关的忽略
3. 禁止死分支：每个 Tool 节点的输出必须被至少一个 LLM 节点通过 {{#tool_xxx.output#}} 引用
4. 复杂度：simple 约 3-5 节点，moderate 约 5-8，full 可含条件分支

【自检与输出】
- 生成初版后请调用 validate_workflow 工具传入该 JSON 字符串进行校验；若返回非 OK，根据问题修正后再次校验，直到返回 OK 或已迭代 2 次
- 本任务只需输出工作流 JSON，请勿使用 read_file、write_file、execute、task 等工具
- 最终必须以 ```json 代码块输出完整工作流 JSON，确保可被 json.loads() 解析
