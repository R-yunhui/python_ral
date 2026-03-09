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
5. Code 节点按需使用：仅当下游 Tool/API 需要 LLM JSON 输出的独立子字段作为参数时才插入 Code 节点。纯意图路由场景（Condition 只需判断意图类别），让 LLM 直接输出纯文本意图标签，Condition 用 contains 匹配即可，不要用 Code 节点
6. 代码节点容错（使用 Code 时）：json.loads 必须包含 try-except，返回安全默认值；必须输出 parse_ok 等决策标志字段
7. 工具调用前必须有条件守卫（使用 Code 时）：当 Tool/MCP 节点的参数依赖 Code 解析结果时，Code 和 Tool 之间必须插入 Condition 节点，检查数据有效性
8. 条件分支禁止汇聚：条件分支互斥，严禁多个分支汇聚到同一个下游节点（会卡死）。每个分支独立闭环，末尾 LLM 设 output_user=true 直接连回 Input
9. 知识库检索输出引用：下游引用用 {{#knowledge_xxx.retrieved_output#}}（内层 key），不是 {{#knowledge_xxx.retrieved_result#}}（外层组 key）

【输出要求】
- 直接输出完整的毕昇工作流 JSON，以 ```json 代码块包裹，确保可被 json.loads() 解析
- 不要输出任何分析过程、解释说明或其他文本，只输出 JSON
- 严格遵守上述设计原则和 SKILL.md 中的规范
