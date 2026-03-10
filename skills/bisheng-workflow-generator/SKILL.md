---
name: bisheng-workflow-generator
description: 专业的毕昇 (BiSheng) 工作流 JSON 文件生成器，根据用户业务需求自动生成完整的毕昇工作流配置文件。当用户提到毕昇、bisheng、毕升工作流、workflow JSON 生成时自动触发。支持多种节点类型（LLM、知识库检索、工具调用、条件分支、代码执行等）和多轮对话模式。
---

## 毕昇工作流 JSON 结构

### 顶层结构
```json
{
  "status": 2,
  "user_id": 1,
  "description": "工作流描述",
  "guide_word": null,
  "name": "工作流名称",
  "logo": "",
  "flow_type": 10,
  "create_time": "2026-01-01T00:00:00",
  "update_time": "2026-01-01T00:00:00",
  "id": "32 位唯一 ID",
  "nodes": [],
  "edges": [],
  "viewport": {"x": 400, "y": 300, "zoom": 0.5}
}
```

## 节点类型

| 类型 | 说明 | 必需 |
|------|------|------|
| `start` | 开始节点 | 是 |
| `input` | 输入节点 | 是 |
| `output` | 输出节点 | 仅在需要输出文件/表单/富文本时 |
| `llm` | 大语言模型节点 | 否 |
| `condition` | 条件判断节点 | 否 |
| `knowledge_retriever` | 知识库检索节点 | 否 |
| `tool` | 工具节点 | 否 |
| `code` | 代码执行节点 | 否 |

## 通用节点结构

```json
{
  "id": "类型_随机后缀",
  "data": {
    "v": "版本号",
    "id": "与外层 id 一致",
    "name": "节点名称",
    "type": "节点类型",
    "description": "节点描述（必需）",
    "group_params": []
  },
  "type": "flowNode",
  "position": {"x": 100, "y": 200},
  "measured": {"width": 334, "height": 500}
}
```

**⚠️ 关键要求**：
1. `data.id` 必须与外层 `id` 逐字符一致
2. `position` 和 `measured` 必需（否则导入报错）
3. `data.description` 必需

**ID 命名**：`类型_随机后缀`（如 `start_654ad`、`llm_ad8b7`）

> 各节点完整 JSON 示例见 [references/node-examples.md](references/node-examples.md)

---

## 节点要点速查

### 1. Start 开始节点（必需）

工作流起始点，包含开场引导和全局变量。

**必需字段**：`guide_word`（开场白）、`guide_question`（引导问题列表）、5 个全局变量（`user_info`、`current_time`、`chat_history`、`preset_question`、`custom_variables`）

⚠️ `preset_question` 的 value 必须是对象数组 `[{"key": "pq_001", "value": "问题"}]`，不是纯字符串数组

---

### 2. Input 输入节点（必需）

接收用户输入，支持对话框和表单两种形式。

**关键要求**：
- `tab`：必须含 `dialog_input` 和 `form_input` 两个 options（含 `help` 字段）
- `description`：固定为 `"接收用户在会话页面的输入，支持 2 种形式：对话框输入，表单输入。"`
- `group_params`：**必须包含 4 个分组**（接收文本、文件上传 groupKey=inputfile、推荐问题 groupKey=custom、表单输入），缺一不可
- `measured.height`: 657

---

### 3. LLM 节点（常用）

调用大模型处理任务。

**关键要求**：
- `tab.options` 只含 `key` 和 `label`，**不含 `help`**（与 Input 不同）
- `user_prompt` 使用 `{{#节点ID.变量名#}}` 引用变量，需含 `varZh`
- `output` 必须包含 `global` 映射
- 提示词分组必须包含 `image_prompt`
- `measured.height`: 836

**group_params 顺序（严格）**：
1. `{params: [batch_variable]}` ← 无 name，第一个分组
2. `{name: "模型设置", params: [model_id, temperature]}`
3. `{name: "提示词", params: [system_prompt, user_prompt, image_prompt]}`
4. `{name: "输出", params: [output_user, output]}`

**`output_user` 规则**：
- `true`：LLM 输出即最终答复 → 直接连回 Input（流式输出，无需 Output 节点）
- `false`：LLM 输出是中间结果 → 连到下一节点

---

### 4. Knowledge Retriever 知识库检索节点

从知识库检索相关内容。

**关键要求**：
- `v` 为**整数** `2`（不是字符串 `"2"`）
- `knowledge` 必须嵌套结构：`{"type": "knowledge", "value": [...]}`
- `user_question` 必须含 `varZh`、`help`、`test`、`global: "self=user_prompt"`、`linkage: "retrieved_result"`
- `metadata_filter` 和 `advanced_retrieval_switch` 为必填字段
- 下游引用：✅ `{{#knowledge_xxx.retrieved_output#}}`（内层 key） ❌ `{{#knowledge_xxx.retrieved_result#}}`（外层组名）

---

### 5. Tool 工具节点

调用外部工具。只使用上下文中明确提供的工具或内置工具（如 `web_search`）。

**关键要求**：
- `tool_key` 必须与上下文完全一致（MCP 工具含 `_数字ID` 后缀，禁止截断）
  - ✅ `"get-stations-code-in-city_28785811"` ❌ `"get-stations-code-in-city"`
- 每个工具节点的输出必须被至少一个下游节点引用（在 LLM、Code 等节点的输入中使用 `{{#工具节点ID.output#}}`），禁止死分支
- 用户/查询类参数（省市区、时间、关键词等）**禁止写死**，必须留空或绑定变量
- `data.id` 必须与外层 `id` 逐字符完全相同
- MCP 工具参数含 `desc` 字段（参数描述）
- 禁止编造不存在的工具

---

### 6. Output 输出节点

向用户发送结果。**仅在需要输出文件、表单、富文本时使用**。

**关键要求**：
- `message`：`{"msg": "{{#llm_xxx.output#}}", "files": []}`
- `output_result`：必须包含 `options: []`
- 纯文本回答直接用 LLM 的 `output_user=true` 流式输出，不接 Output 节点

**多分支场景**：每个分支末尾 LLM 设 `output_user=true` 连回 Input。❌ **禁止**多分支汇聚到同一 Output 节点。

---

### 7. Condition 条件判断节点

根据条件执行不同分支。推荐用 `contains` 而非 `equals`（LLM 输出可能含换行/空格）。

**关键要求**：
- `value` 数组**只放有实际条件的分支**，兜底统一用 `right_handle` 出边
- ❌ 禁止 `conditions: []` 空条件分支（导入报「条件分支不可为空」）
- 出边：有条件分支 sourceHandle = 分支 `id`，兜底 sourceHandle = `"right_handle"`
- 边 ID 格式：`xy-edge__源节点ID分支ID-目标节点IDleft_handle`

---

### 8. Code 代码节点

执行自定义 Python 代码，用于 JSON 解析、数据转换、字段提取。

**✅ 需要使用的场景**：
- Tool/API 需要 LLM JSON 输出的独立子字段作为参数
- 复杂业务逻辑需基于多字段组合计算

**❌ 不需要使用的场景**：
- 纯意图路由（Condition 直接 `contains` 匹配 LLM 文本输出）
- 知识库检索（直接用 `input.user_input`）
- 下游 LLM 引用完整输出

**group_params 顺序**：入参 → 执行代码 → 出参

**代码规范（必须遵守）**：
1. 必须 try-except 容错，返回安全默认值
2. 必须输出 `parse_ok` 等决策标志，供下游条件判断
3. 必须处理 Markdown ` ```json ``` ` 包裹（正则剥离）
4. 函数签名：`def main(参数名: 类型) -> dict:`，return dict 的 key 与 code_output 声明一致
5. 类型兜底：`str(data.get("xxx") or "")`

---

## 平台限制与解决模式

### LLM 输出的 JSON 子属性不可直接引用

✅ `{{#llm_xxx.output#}}`（完整字符串） ❌ `{{#llm_xxx.output.city#}}`（无效）

需通过 Code 节点解析后引用 `{{#code_xxx.city#}}`。

### 模式选择

| 下游需求 | 推荐模式 |
|---------|---------|
| Condition 只需判断意图类别 | **模式 A：简单分支**（无 Code） |
| 知识库用用户原始输入检索 | **模式 A** |
| 下游 LLM 引用完整输出 | 直接引用 `llm_xxx.output` |
| Tool/API 需要独立参数 | **模式 B：Code 守卫** |
| 需要组合多字段计算 | **模式 B** |

### 模式 A：简单分支（无 Code，推荐用于纯意图路由）

```
Input → LLM(意图分析, 输出纯文本标签如 "policy_query")
      → Condition(对 llm_xxx.output 做 contains 匹配)
        ├─ contains "policy"  → KB(user_input检索) → LLM(output_user=true) → Input
        ├─ contains "company" → LLM(output_user=true) → Input
        └─ right_handle(兜底) → LLM(output_user=true) → Input
```

### 模式 B：Code 守卫（当 Tool/API 需要独立子字段时）

```
LLM(输出JSON) → Code(容错解析 + 字段提取 + 决策标志)
  → Condition(检查 parse_ok + 业务标志)
    ├─ should_query="true" → Tool(使用 code_xxx.province/city) → LLM(output_user=true) → Input
    └─ right_handle(兜底) → LLM(引导补充信息, output_user=true) → Input
```

**三件套**：断言（Code 输出标志）→ 守卫（Condition 检查标志）→ 降级（兜底引导用户）

---

## Edges 边连接

```json
{
  "id": "xy-edge__源节点ID源句柄-目标节点ID目标句柄",
  "type": "customEdge",
  "source": "源节点ID",
  "target": "目标节点ID",
  "sourceHandle": "right_handle",
  "targetHandle": "left_handle",
  "animated": true
}
```

**核心规则**：
1. 支持并行 Fan-out / Fan-in，但**每个并行分支节点必须有出边**（否则 fan-in 卡死）
2. **条件分支互斥，禁止多个分支汇聚到同一下游节点**（未执行分支无输出，会卡死）。每个条件分支独立闭环（LLM `output_user=true` 连回 Input）
3. 成环/循环支持：末端 LLM（`output_user=true`）连回 Input 形成多轮对话
4. 使用 Output 节点时，必须包含 Output→Input 循环边

---

## Position 节点布局

**水平布局**：列间距 **834px**，起始 X = **-200**

**垂直布局**：
- 分支 Y 坐标：109, 882, 1655...（每个 +773px）
- Condition 节点 Y = 所有分支 Y 的平均值（居中）

```python
branch_y_coords = [109 + i * 773 for i in range(n)]
condition_y = (branch_y_coords[0] + branch_y_coords[-1]) / 2
```

**示例坐标**：
```
Start(-200, 282) → Input(634, 382) → LLM(1468, 109) → Condition(2302, 500)
  ├─ Branch_A(3136, 109)
  ├─ Branch_B(3136, 882)
  └─ Branch_C(3136, 1655)
```

---

## 必须遵守的规则

1. `data.id` 与外层 `id` 逐字符一致
2. 每个节点必须有 `description`、`position`、`measured`
3. 变量引用：`{{#节点ID.变量名#}}`（注意 `#` 符号）
4. **禁止引用 LLM 子属性**：`{{#llm_xxx.output.字段名#}}` 无效！需 Code 节点解析
5. Code 节点按需使用：纯意图路由不需要
6. 所有节点必须有出边，禁止死分支（每条分支最终必须回环到 Input 节点形成多轮对话闭环）
7. 条件分支独立闭环，禁止汇聚（每个分支末尾 LLM `output_user=true` 连回 Input）
8. `knowledge` 字段嵌套结构；`knowledge_retriever.v` 为整数 `2`
9. Tool `tool_key` 完整保留（MCP 含 `_数字ID` 后缀）；禁止编造不存在的工具；每个工具节点的输出必须被至少一个下游节点（如 LLM、Code）引用
10. Tool 用户/查询类参数禁止写死
11. Code 代码必须容错 + 决策标志 + 处理 Markdown 包裹
12. 工具调用前必须有 Condition 守卫
13. 每条分支必须回环到已在流程中的节点（通常是 Input）形成多轮对话回环，禁止末端节点悬空无出边
14. Condition 节点所有触点（含 `right_handle`）必须有出边连线。即使该分支不做任何事，也要通过 LLM(`output_user=true`)回环连回 Input

## 常见错误速查

- ❌ Input `group_params` 只有接收文本 → ✅ 必须 4 个分组
- ❌ LLM `tab.options` 含 `help` → ✅ 只含 `key` 和 `label`
- ❌ LLM `batch_variable` 放在输出分组 → ✅ 第一个无名分组
- ❌ LLM 提示词分组缺 `image_prompt` → ✅ 必须包含
- ❌ `knowledge_retriever.v` 写成字符串 `"2"` → ✅ 整数 `2`
- ❌ 下游用 `knowledge_xxx.retrieved_result` → ✅ 用 `retrieved_output`
- ❌ MCP `tool_key` 截断数字后缀 → ✅ 完整保留
- ❌ 工具节点输出未被任何下游节点引用 → ✅ 在至少一个下游节点（如 LLM、Code）的输入中引用 `{{#工具节点ID.output#}}`
- ❌ Code 裸调用 `json.loads` 无 try-except → ✅ 必须容错
- ❌ Condition `value` 末尾加空 `conditions: []` → ✅ 兜底用 `right_handle` 出边
- ❌ 多条件分支汇聚到同一 Output → ✅ 各分支独立闭环（LLM `output_user=true` 连回 Input）
- ❌ Condition `right_handle` 悬空无连线 → ✅ 必须通过 LLM(`output_user=true`)回环连回 Input
- ❌ 分支末端节点悬空无出边 → ✅ 所有分支必须回环到 Input 形成多轮对话

---

## 输出格式

生成可直接导入毕昇平台的完整 JSON。默认多轮对话（含循环边），除非用户明确要求单次执行。

### 质量标准

**合格**：JSON 正确、nodes/edges 完整、节点连接无死分支、变量引用正确、position/measured/description 齐全

**优秀**：提示词专业、布局美观、模式选择正确（A/B）、Code 带容错和决策标志、Tool 前有 Condition 守卫

---

## 参考资料

- **各节点完整 JSON 示例**：[references/node-examples.md](references/node-examples.md) — 生成工作流时读取
- **字段格式规范与校验清单**：[references/field-format-spec.md](references/field-format-spec.md) — 验证字段格式时读取
- **简单分支模式完整示例**：[references/personal-travel-assistant.json](references/personal-travel-assistant.json)
- **Code 守卫模式完整示例**：[references/code-guard-tool-pattern.json](references/code-guard-tool-pattern.json)
