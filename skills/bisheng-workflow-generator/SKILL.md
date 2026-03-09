---
name: bisheng-workflow-generator
description: 专业的毕昇 (BiSheng) 工作流 JSON 文件生成器，根据用户业务需求自动生成完整的毕昇工作流配置文件。当用户提到毕昇、bisheng、毕升工作流时自动触发。
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

**必填字段**:
- `status`: 2 (已发布)
- `flow_type`: 10 (标准工作流)
- `id`: 32 位唯一 ID
- `nodes`: 节点列表（每个节点必须包含 position 和 measured）
- `edges`: 边连接列表
- `guide_word`: 顶层占位字段，通常为 `null`（开场白内容在 start 节点内配置）
- `logo`: 空字符串 `""`
- `create_time` / `update_time`: ISO 格式时间字符串

## 节点类型

| 类型 | 说明 | 必需 |
|------|------|------|
| `start` | 开始节点 | 是 |
| `input` | 输入节点 | 是 |
| `output` | 输出节点 | 是 |
| `llm` | 大语言模型节点 | 否 |
| `condition` | 条件判断节点 | 否 |
| `knowledge_retriever` | 知识库检索节点 | 否 |
| `tool` | 工具节点 | 否 |
| `code` | 代码执行节点 | 否 |

## 节点详解

### 通用节点结构（重要）

**每个节点必须包含以下字段**：
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
1. `data.id` 必须与外层 `id` 一致
2. `data.description` 必需
3. `position` 必需（否则导入报错）
4. `measured` 必需（否则导入报错）

**ID 命名规范**: `类型_随机后缀`（如 `start_654ad`、`llm_ad8b7`）

**布局规则**：
- 列间距：834px
- 起始 X：-200
- 分支间距：≥600px

---

### 1. Start 开始节点（必需）

**作用**：工作流起始点，包含开场引导和全局变量。

**必需字段**：
- `guide_word`：开场白
- `guide_question`：引导问题列表
- 5 个全局变量：`user_info`、`current_time`、`chat_history`、`preset_question`、`custom_variables`

**完整示例**：
```json
{
  "id": "start_654ad",
  "data": {
    "v": "3",
    "id": "start_654ad",
    "name": "开始",
    "type": "start",
    "description": "工作流运行的起始节点。",
    "group_params": [
      {
        "name": "开场引导",
        "params": [
          {"key": "guide_word", "type": "textarea", "label": "true", "value": "欢迎语", "placeholder": "true"},
          {"key": "guide_question", "type": "input_list", "label": "true", "value": ["问题 1", "问题 2"], "placeholder": "true"}
        ]
      },
      {
        "name": "全局变量",
        "params": [
          {"key": "user_info", "type": "var", "label": "true", "value": "", "global": "key"},
          {"key": "current_time", "type": "var", "label": "true", "value": "", "global": "key"},
          {"key": "chat_history", "type": "chat_history_num", "value": 10, "global": "key"},
          {"key": "preset_question", "help": "true", "type": "input_list", "label": "true", "value": [{"key": "pq_001", "value": "问题 1"}], "global": "item:input_list", "placeholder": "true"},
          {"key": "custom_variables", "help": "true", "type": "global_var", "label": "true", "value": [], "global": "item:input_list"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": -200, "y": 282},
  "measured": {"width": 334, "height": 600}
}
```

---

### 2. Input 输入节点（必需）

**作用**：接收用户输入，支持对话框输入和表单输入两种形式。

**核心字段**：
- `tab`：必须包含 2 个 options（`dialog_input` 和 `form_input`），options 里有 `help` 字段
- `description`：必须为 `"接收用户在会话页面的输入，支持 2 种形式：对话框输入，表单输入。"`
- `group_params`：必须包含 4 个分组，缺一不可

**4 个分组说明**：
| 分组 | groupKey | 作用 |
|------|----------|------|
| 接收文本 | 无 | 接收用户文字输入 `user_input` |
| 文件上传 | `inputfile` | 接收文件、图片上传相关配置 |
| 推荐问题 | `custom` | AI 自动推荐下一步问题的配置 |
| 表单输入 | 无 | 表单模式输入 `form_input` |

**完整示例**：
```json
{
  "id": "input_1efc6",
  "data": {
    "v": "3",
    "id": "input_1efc6",
    "tab": {
      "value": "dialog_input",
      "options": [
        {"key": "dialog_input", "help": "true", "label": "true"},
        {"key": "form_input", "help": "true", "label": "true"}
      ]
    },
    "name": "输入",
    "type": "input",
    "description": "接收用户在会话页面的输入，支持 2 种形式：对话框输入，表单输入。",
    "group_params": [
      {
        "name": "接收文本",
        "params": [
          {"key": "user_input", "tab": "dialog_input", "type": "var", "label": "true", "global": "key"}
        ]
      },
      {
        "name": "",
        "groupKey": "inputfile",
        "params": [
          {"key": "user_input_file", "tab": "dialog_input", "value": false, "groupTitle": true},
          {"key": "file_parse_mode", "tab": "dialog_input", "type": "select_parsemode", "value": "extract_text"},
          {"key": "dialog_files_content", "tab": "dialog_input", "type": "var", "label": "true", "global": "key"},
          {"key": "dialog_files_content_size", "min": 0, "tab": "dialog_input", "type": "char_number", "label": "true", "value": 15000},
          {"key": "dialog_file_accept", "tab": "dialog_input", "type": "select_fileaccept", "label": "true", "value": "file"},
          {"key": "dialog_image_files", "tab": "dialog_input", "help": "true", "type": "var", "label": "true", "global": "key", "hidden": true},
          {"key": "dialog_file_paths", "tab": "dialog_input", "help": "true", "type": "var", "label": "true", "global": "key"}
        ]
      },
      {
        "name": "",
        "groupKey": "custom",
        "params": [
          {"key": "recommended_questions_flag", "tab": "dialog_input", "help": "true", "label": "true", "value": true, "hidden": "true", "groupTitle": true},
          {"key": "recommended_llm", "tab": "dialog_input", "type": "bisheng_model", "label": "true", "value": 5, "required": true, "placeholder": "true"},
          {"key": "recommended_system_prompt", "tab": "dialog_input", "type": "var_textarea", "label": "true", "value": "# Role\n你是一个极具洞察力的\"对话延续预测专家\"。你的任务是根据当前的对话历史，预测用户接下来最有可能输入的 3 条短语或问题。\n\n# Output Format\n请严格遵守 JSON 格式输出，返回包含单一键名 \"suggestions\" 的 JSON 对象。\n不要输出 Markdown 代码块标记，直接输出 JSON 字符串。\n**示例：**\n{\"suggestions\": [\"你能举个例子吗？\", \"这个方案的成本是多少？\", \"听起来不错，怎么开始？\"]}", "required": true},
          {"key": "recommended_history_num", "tab": "dialog_input", "help": "true", "step": 1, "type": "slide", "label": "true", "scope": [1, 10], "value": 2}
        ]
      },
      {
        "name": "",
        "params": [
          {"key": "form_input", "tab": "form_input", "type": "form", "label": "true", "value": [], "global": "item:form_input"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 634, "y": 382},
  "measured": {"width": 334, "height": 657}
}
```

**⚠️ 常见错误**：
- ❌ group_params 只有 `接收文本` 一个分组 → ✅ 必须包含全部 4 个分组
- ❌ `measured.height` 设为 268 → ✅ 完整节点高度为 657

---

### 3. LLM 节点（常用）

**作用**：调用大模型处理任务。

**核心字段**：
- `tab`：必需，options 只含 `key` 和 `label`，**不含 `help`**
- `model_id`：模型 ID（必需）
- `user_prompt`：用户提示词（必需，使用 `{{#节点 ID.变量名#}}` 引用变量）
- `output`：输出变量（必需包含 `global` 映射）
- `batch_variable`：必需，放在**第一个无名分组**中（不是输出分组）
- `image_prompt`：提示词分组必须包含此字段

**group_params 顺序（严格遵守）**：
1. `{"params": [batch_variable]}` ← 无 name，第一个分组
2. `{"name": "模型设置", "params": [model_id, temperature]}`
3. `{"name": "提示词", "params": [system_prompt, user_prompt, image_prompt]}`
4. `{"name": "输出", "params": [output_user, output]}`

**完整示例**：
```json
{
  "id": "llm_ad8b7",
  "data": {
    "v": "2",
    "id": "llm_ad8b7",
    "name": "AI 回答",
    "type": "llm",
    "description": "调用大模型回答用户问题。",
    "tab": {
      "value": "single",
      "options": [
        {"key": "single", "label": "true"},
        {"key": "batch", "label": "true"}
      ]
    },
    "group_params": [
      {
        "params": [
          {"key": "batch_variable", "tab": "batch", "help": "true", "test": "var", "type": "user_question", "label": "true", "value": [], "global": "self", "linkage": "output", "required": true, "placeholder": "true"}
        ]
      },
      {
        "name": "模型设置",
        "params": [
          {"key": "model_id", "type": "bisheng_model", "label": "true", "value": 5, "required": true, "placeholder": "true"},
          {"key": "temperature", "step": 0.1, "type": "slide", "label": "true", "scope": [0, 2], "value": 0.7}
        ]
      },
      {
        "name": "提示词",
        "params": [
          {"key": "system_prompt", "test": "var", "type": "var_textarea", "label": "true", "value": "你是专业的 AI 助手"},
          {"key": "user_prompt", "test": "var", "type": "var_textarea", "label": "true", "value": "用户问题：{{#input_1efc6.user_input#}}", "varZh": {"input_1efc6.user_input": "输入/user_input"}, "required": true},
          {"key": "image_prompt", "help": "true", "type": "image_prompt", "label": "true", "value": []}
        ]
      },
      {
        "name": "输出",
        "params": [
          {"key": "output_user", "help": "true", "type": "switch", "label": "true", "value": true},
          {"key": "output", "help": "true", "type": "var", "label": "true", "value": [], "global": "code:value.map(el => ({ label: el.label, value: el.key }))"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 1468, "y": 109},
  "measured": {"width": 334, "height": 836}
}
```

**⚠️ 常见错误**：
- ❌ `tab.options` 中含有 `help: "true"` → ✅ options 只含 `key` 和 `label`
- ❌ `batch_variable` 放在 `输出` 分组 → ✅ 必须在第一个无名分组
- ❌ `提示词` 分组缺少 `image_prompt` → ✅ 必须包含
- ❌ `measured.height` 设为 700 → ✅ 完整节点高度为 836

**变量引用格式**：`{{#节点 ID.变量名#}}`

---

### 4. Knowledge Retriever 知识库检索节点（常用）

**作用**：从指定知识库中检索相关内容。

**⚠️ 重要**：`v` 字段为**整数** `2`，不是字符串 `"2"`（与 LLM 节点不同）

**核心字段**：
- `user_question`：检索问题（必需，引用上游变量，需含 `varZh`、`help`、`test`、`global`、`linkage`）
- `knowledge`：知识库选择（必需，嵌套结构）
- `metadata_filter`：元数据过滤（必需，默认 disabled）
- `advanced_retrieval_switch`：检索参数（必需，含权重、rerank 等配置）
- `retrieved_result`：输出字段（必需包含 global 映射，value 格式为对象数组）

**完整示例**：
```json
{
  "id": "knowledge_retriever_xxx",
  "data": {
    "v": 2,
    "id": "knowledge_retriever_xxx",
    "name": "知识库检索",
    "type": "knowledge_retriever",
    "description": "根据用户问题从知识库中检索相关内容，结合检索结果调用大模型生成最终结果，支持多个问题并行执行。",
    "group_params": [
      {
        "name": "知识库检索设置",
        "params": [
          {
            "key": "user_question",
            "help": "true",
            "test": "var",
            "type": "user_question",
            "label": "true",
            "value": ["llm_xxx.output"],
            "varZh": {"llm_xxx.output": "上游节点名称/output"},
            "global": "self=user_prompt",
            "linkage": "retrieved_result",
            "required": true,
            "placeholder": "true"
          },
          {
            "key": "knowledge",
            "type": "knowledge_select_multi",
            "label": "true",
            "value": {
              "type": "knowledge",
              "value": [{"key": 6, "label": "知识库名称"}]
            },
            "required": true,
            "placeholder": "true"
          },
          {
            "key": "metadata_filter",
            "type": "metadata_filter",
            "label": "true",
            "value": {"enabled": false}
          },
          {
            "key": "advanced_retrieval_switch",
            "type": "search_switch",
            "label": "true",
            "value": {
              "keyword_weight": 0.4,
              "vector_weight": 0.6,
              "user_auth": false,
              "search_switch": true,
              "rerank_flag": false,
              "rerank_model": "",
              "max_chunk_size": 15000
            }
          }
        ]
      },
      {
        "name": "输出",
        "params": [
          {
            "key": "retrieved_result",
            "type": "var",
            "label": "true",
            "value": [{"key": "retrieved_output", "label": "retrieved_output"}],
            "global": "code:value.map(el => ({ label: el.label, value: el.key }))"
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 1200, "y": 282},
  "measured": {"width": 334, "height": 781}
}
```

**注意事项**：
1. `v` 字段是整数 `2`，不是字符串 `"2"`
2. `knowledge` 字段必须使用嵌套结构（`type: "knowledge"` + `value: [...]`）
3. `user_question` 必须包含 `varZh`，引用上游节点的输出变量
4. `metadata_filter` 和 `advanced_retrieval_switch` 为必填字段，使用默认值即可
5. `retrieved_result` 的 value 格式为 `[{"key": "retrieved_output", "label": "retrieved_output"}]`
6. **⚠️ 下游引用输出时，用内层 key `retrieved_output`，不是外层 key `retrieved_result`**：
   - ✅ 正确：`{{#knowledge_xxx.retrieved_output#}}`
   - ❌ 错误：`{{#knowledge_xxx.retrieved_result#}}`（`retrieved_result` 是输出组名，不是变量名）

---

### 5. Tool 工具节点（可选）

**作用**：调用外部工具。

**重要**：只使用上下文中明确提供的工具，或毕昇平台内置工具（如 `web_search`）！

**工具类型与 `tool_key` 格式**：

毕昇平台支持两类工具，`tool_key` 格式不同：

| 类型 | `tool_key` 格式 | 示例 |
|------|----------------|------|
| 内置工具 | 简短名称 | `web_search` |
| MCP 工具 | `{工具名}_{数字ID}` | `get-stations-code-in-city_28785811` |

**⚠️ `tool_key` 必须与上下文提供的值完全一致，禁止省略、修改或截断任何部分（包括 MCP 工具末尾的 `_数字ID` 后缀）**

```json
// ✅ 正确：上下文给了 "get-stations-code-in-city_28785811"，原样使用
"tool_key": "get-stations-code-in-city_28785811"

// ❌ 错误：截断了数字 ID 后缀
"tool_key": "get-stations-code-in-city"
```

**内置工具示例（`web_search`）**：
```json
{
  "id": "tool_982ee",
  "data": {
    "id": "tool_982ee",
    "name": "联网搜索",
    "type": "tool",
    "tool_key": "web_search",
    "description": "使用 query 进行联网检索并返回结果。",
    "group_params": [
      {
        "name": "工具参数",
        "params": [
          {"key": "query", "test": "input", "type": "var_textarea", "label": "query", "value": "{{#input_1efc6.user_input#}}", "required": true}
        ]
      },
      {
        "name": "输出",
        "params": [
          {"key": "output", "type": "var", "label": "输出变量", "value": "", "global": "key"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 850, "y": 282},
  "measured": {"width": 334, "height": 430}
}
```

**MCP 工具示例**：
```json
{
  "id": "tool_a1be2",
  "data": {
    "id": "tool_a1be2",
    "name": "get-stations-code-in-city",
    "type": "tool",
    "tool_key": "get-stations-code-in-city_28785811",
    "description": "通过中文城市名查询该城市所有火车站的名称及其对应的 station_code。",
    "group_params": [
      {
        "name": "工具参数",
        "params": [
          {"key": "city", "desc": "中文城市名称", "test": "input", "type": "var_textarea", "label": "city", "value": "{{#input_1efc6.user_input#}}", "varZh": {"input_1efc6.user_input": "输入/user_input"}, "required": true}
        ]
      },
      {
        "name": "输出",
        "params": [
          {"key": "output", "type": "var", "label": "输出变量", "value": "", "global": "key"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 850, "y": 282},
  "measured": {"width": 334, "height": 430}
}
```

**MCP 工具参数说明**：
- MCP 工具的参数来自上下文提供的 `参数` 列表，每个参数的 `key` 对应参数名称
- 参数的 `desc` 字段为参数描述（MCP 工具特有）
- 当参数值引用上游变量时，使用 `{{#节点ID.变量名#}}` 格式，并添加 `varZh` 映射

**警告**：不要编造不存在的工具（如 `weather_query`）

**⚠️ data.id 必须与外层 id 逐字符完全相同**，生成时先确定外层 id，再原样复制到 `data.id`，不得增减任何前缀或后缀：
```json
// ✅ 正确
{"id": "tool_realtime_e5f6", "data": {"id": "tool_realtime_e5f6", ...}}

// ❌ 错误（data.id 丢失前缀）
{"id": "tool_realtime_e5f6", "data": {"id": "tool_e5f6", ...}}
```

---

### 6. Output 输出节点（必需）

**作用**：向用户发送结果，是工作流的自然结束点。

**何时使用 Output 节点**：需要输出文件、表单、或富文本格式时使用。**如果 LLM 的输出就是最终答复，直接将 LLM 的 `output_user` 设为 `true` 并连回 Input，跳过 Output 节点**——这样可以保留流式输出，用户体验更好。

**核心字段**：
- `message`：输出内容（必需，包含 `msg` 和 `files`）
- `output_result`：输出表单（必需，必须包含 `options: []`）

**完整示例**：
```json
{
  "id": "output_5b20b",
  "data": {
    "v": "2",
    "id": "output_5b20b",
    "name": "输出",
    "type": "output",
    "description": "向用户发送文本和文件。",
    "group_params": [
      {
        "params": [
          {"key": "message", "type": "var_textarea_file", "label": "true", "value": {"msg": "{{#llm_ad8b7.output#}}", "files": []}, "varZh": {"llm_ad8b7.output": "AI 回答/output"}, "global": "key", "required": true, "placeholder": "true"},
          {"key": "output_result", "type": "output_form", "label": "用户输入内容", "value": {"type": "", "value": ""}, "global": "value.type=input", "options": [], "required": false}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 2302, "y": 300},
  "measured": {"width": 334, "height": 465}
}
```

**注意**：毕昇不需要专门的 End 节点，Output 节点仅用于需要输出**文件、表单、富文本**的场景。纯文本回答使用 LLM 节点的 `output_user=true` 直接流式输出，**不接 Output 节点**。

**`output_user` 规则**：
- `true`：该 LLM 的输出就是给用户的最终答复 → 直接连回 Input（流式，无需 Output 节点）
- `false`：该 LLM 的输出是中间结果，还需流转给下一节点（如意图识别）→ 连到下一节点

**多分支场景**：每个分支末尾的 LLM 设 `output_user=true`，直接连回 Input：
```
Condition
  ├─ branch_a → LLM_A（output_user=true）→ Input（循环）
  ├─ branch_b → LLM_B（output_user=true）→ Input（循环）
  └─ right_handle → LLM_C（output_user=true）→ Input（循环）
```

❌ **禁止**多分支汇聚到同一 Output 节点——未激活分支会输出 `None` 字符串

---


### 7. Condition 条件判断节点（常用）

**作用**：根据条件表达式执行不同的分支逻辑。

**比较运算符**：`equals` / `not_equals` / `contains` / `not_contains` / `is_empty` / `is_not_empty` / `greater_than` / `less_than`

> **⚠️ 推荐使用 `contains` 而非 `equals`**：LLM 输出可能携带换行符或空格，`equals` 精确匹配容易失败。

**兜底分支规则（重要）**：
- 毕昇平台**不支持** `conditions: []` 的空条件分支，导入会报「条件分支不可为空」
- **无论几个分支，兜底（else）统一用 `right_handle` 出边**，不要在 `value` 数组里添加空 conditions 的兜底项
- `value` 数组里**只放有实际条件的分支**

**完整示例（3 个有条件分支 + 1 个 right_handle 兜底）**：

```json
{
  "id": "condition_xxx",
  "data": {
    "v": "1",
    "id": "condition_xxx",
    "name": "意图分支",
    "type": "condition",
    "description": "根据条件表达式执行不同的分支。",
    "group_params": [
      {
        "params": [
          {
            "key": "condition",
            "type": "condition",
            "label": "true",
            "value": [
              {
                "id": "branch_a",
                "operator": "or",
                "conditions": [
                  {
                    "id": "cond_a_1",
                    "left_var": "llm_xxx.output",
                    "left_label": "意图识别/output",
                    "right_value": "A",
                    "right_value_type": "input",
                    "comparison_operation": "contains"
                  }
                ]
              },
              {
                "id": "branch_b",
                "operator": "or",
                "conditions": [
                  {
                    "id": "cond_b_1",
                    "left_var": "llm_xxx.output",
                    "left_label": "意图识别/output",
                    "right_value": "B",
                    "right_value_type": "input",
                    "comparison_operation": "contains"
                  }
                ]
              },
              {
                "id": "branch_c",
                "operator": "or",
                "conditions": [
                  {
                    "id": "cond_c_1",
                    "left_var": "llm_xxx.output",
                    "left_label": "意图识别/output",
                    "right_value": "C",
                    "right_value_type": "input",
                    "comparison_operation": "contains"
                  }
                ]
              }
            ],
            "required": true
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 1600, "y": 500},
  "measured": {"width": 562, "height": 448}
}
```

对应出边（4 条，包含 right_handle 兜底）：
```json
{"source": "condition_xxx", "sourceHandle": "branch_a",     "target": "llm_a_xxx"},
{"source": "condition_xxx", "sourceHandle": "branch_b",     "target": "llm_b_xxx"},
{"source": "condition_xxx", "sourceHandle": "branch_c",     "target": "llm_c_xxx"},
{"source": "condition_xxx", "sourceHandle": "right_handle", "target": "llm_default_xxx"}
```

**边连接规则总结**：
- 有条件的分支：`sourceHandle` = 该分支的 `id`（如 `branch_a`）
- 兜底（else）：`sourceHandle` = `"right_handle"`（固定，不在 value 数组中定义）
- 边 ID 格式：`xy-edge__源节点ID分支ID-目标节点IDleft_handle`

**⚠️ 常见错误**：
- ❌ 在 `value` 末尾加 `{"id": "default_branch", "conditions": []}` → 导入报「条件分支不可为空」
- ❌ 比较运算使用 `equals` 匹配 LLM 输出 → 改用 `contains`



---

### 8. Code 代码节点（常用）

**作用**：在工作流中执行自定义 Python 代码，用于 JSON 解析、数据转换、字段提取、逻辑计算等。

**⚠️ 核心使用场景**：当 LLM 节点输出 JSON 字符串，**且下游 Tool/API 节点需要将其中的独立字段作为单独参数传入**时，**必须**通过代码节点解析后再引用（详见「平台限制与解决模式」章节）。

**❌ 不需要使用 Code 节点的场景**：
- **仅做意图路由**：Condition 节点只需判断意图类别 → 让 LLM 直接输出纯文本意图标签（如 `policy_query`），Condition 用 `contains` 匹配即可
- **知识库检索**：`user_question` 可直接用 `input.user_input`（用户原始输入），无需从 JSON 提取
- **下游 LLM 引用完整输出**：直接用 `{{#llm_xxx.output#}}` 引用整段文本即可

**✅ 需要使用 Code 节点的场景**：
- **Tool/API 需要拆分的参数**：如工具需要 `province`、`city`、`district` 各自作为独立参数
- **复杂业务逻辑**：需要基于多个字段组合计算决策标志（如 `should_query = intent == "company_query" and has_location`）

**核心字段**：
- `v`：`"1"`（字符串）
- `expand`：`true`（布尔）
- `code_input`（入参）：声明输入变量，引用上游节点输出
- `code`（执行代码）：Python 函数，签名为 `def main(...) -> dict:`
- `code_output`（出参）：声明返回字典中的各个 key 及其类型

**group_params 顺序（严格遵守）**：
1. `{"name": "入参", "params": [code_input]}`
2. `{"name": "执行代码", "params": [code]}`
3. `{"name": "出参", "params": [code_output]}`

**code_input 格式说明**：
- `value` 为数组，每项描述一个输入变量
- 每项包含 `key`（代码中的参数名）、`type`（`"ref"` 表示引用上游变量）、`label`（中文说明）、`value`（上游变量路径，如 `"llm_xxx.output"`）

**code_output 格式说明**：
- `value` 为数组，每项描述一个输出字段
- 每项包含 `key`（字段名，对应 return dict 的键）、`type`（`"str"` / `"int"` / `"float"` / `"bool"` / `"list"` / `"dict"`）
- 必须包含 `global` 映射：`"code:value.map(el => ({ label: el.key, value: el.key }))"`
- 下游节点通过 `{{#code_xxx.字段名#}}` 引用

**完整示例（JSON 解析 + 容错 + 决策标志）**：
```json
{
  "id": "code_a1b2c",
  "data": {
    "v": "1",
    "id": "code_a1b2c",
    "name": "解析意图",
    "type": "code",
    "expand": true,
    "description": "解析 LLM 输出的 JSON，提取结构化字段，计算决策标志。",
    "group_params": [
      {
        "name": "入参",
        "params": [
          {
            "key": "code_input",
            "test": "input",
            "type": "code_input",
            "value": [
              {"key": "arg1", "type": "ref", "label": "意图分析/output", "value": "llm_xxx.output"}
            ],
            "required": true
          }
        ]
      },
      {
        "name": "执行代码",
        "params": [
          {
            "key": "code",
            "type": "code",
            "value": "def main(arg1: str) -> dict:\n    import json, re\n    text = arg1.strip()\n    m = re.search(r'```(?:json)?\\s*([\\s\\S]*?)```', text)\n    if m:\n        text = m.group(1).strip()\n    try:\n        data = json.loads(text)\n    except Exception:\n        return {\"intent\": \"\", \"province\": \"\", \"city\": \"\", \"district\": \"\", \"parse_ok\": \"false\", \"should_query\": \"false\"}\n    if not isinstance(data, dict):\n        return {\"intent\": \"\", \"province\": \"\", \"city\": \"\", \"district\": \"\", \"parse_ok\": \"false\", \"should_query\": \"false\"}\n    province = str(data.get(\"province\") or \"\")\n    city = str(data.get(\"city\") or \"\")\n    district = str(data.get(\"district\") or \"\")\n    intent = str(data.get(\"intent\") or \"\")\n    has_loc = any([province, city, district])\n    should_query = \"true\" if intent == \"company_query\" and has_loc else \"false\"\n    return {\"intent\": intent, \"province\": province, \"city\": city, \"district\": district, \"parse_ok\": \"true\", \"should_query\": should_query}",
            "required": true
          }
        ]
      },
      {
        "name": "出参",
        "params": [
          {
            "key": "code_output",
            "type": "code_output",
            "value": [
              {"key": "intent", "type": "str"},
              {"key": "province", "type": "str"},
              {"key": "city", "type": "str"},
              {"key": "district", "type": "str"},
              {"key": "parse_ok", "type": "str"},
              {"key": "should_query", "type": "str"}
            ],
            "global": "code:value.map(el => ({ label: el.key, value: el.key }))",
            "required": true
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 2302, "y": 500},
  "measured": {"width": 334, "height": 690}
}
```

**代码编写规范（必须遵守）**：
1. **必须包含 try-except**：`json.loads` 等操作必须捕获异常，返回安全默认值，禁止裸调用
2. **必须输出决策标志字段**：如 `parse_ok`（解析是否成功）、`should_query`（是否满足调用条件），供下游条件节点做简单判断
3. **必须做类型兜底**：用 `str(data.get("xxx") or "")` 确保输出类型与 code_output 声明一致
4. **必须处理 Markdown 包裹**：LLM 常用 ` ```json ... ``` ` 包裹输出，代码中需用正则剥离
5. **函数签名**：`def main(参数名: 类型) -> dict:`，返回 dict 的键必须与 code_output 中声明的 key 一一对应

**简单 JSON 解析模板（最小版本）**：
```python
def main(arg1: str) -> dict:
    import json, re
    text = arg1.strip()
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        text = m.group(1).strip()
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("not a dict")
    except Exception:
        return {"field1": "", "field2": "", "parse_ok": "false"}
    return {
        "field1": str(data.get("field1") or ""),
        "field2": str(data.get("field2") or ""),
        "parse_ok": "true"
    }
```

**⚠️ 常见错误**：
- ❌ 裸调用 `json.loads` 无 try-except → 解析失败工作流崩溃
- ❌ 缺少 `parse_ok` 等决策标志 → 下游无法判断数据有效性
- ❌ 未处理 Markdown 代码块包裹 → LLM 输出 ` ```json...``` ` 时解析失败
- ❌ code_output 声明的 key 与 return dict 的 key 不一致 → 下游取不到值
- ❌ 返回 None 或非 dict → 工作流异常
- ❌ `measured.height` 设为 500 → ✅ 完整节点高度为 690

---

## 平台限制与解决模式

### 限制：LLM 输出的 JSON 子属性不可直接引用

毕昇平台中，LLM 节点的输出始终是一个**完整字符串**。即使 LLM 输出了标准 JSON（如 `{"intent": "query", "city": "深圳"}`），下游节点：
- ✅ **可以**引用完整输出：`{{#llm_xxx.output#}}`
- ❌ **不可以**引用 JSON 内部字段：`{{#llm_xxx.output.city#}}`（无效，取到的是空值或字面文本）

### 选择模式：根据下游是否需要独立子字段决定

**先判断下游节点是否需要 LLM JSON 输出的独立子字段**：

| 下游需求 | 是否需要 Code 节点 | 推荐模式 |
|---------|------------------|---------|
| Condition 只需判断意图类别 | ❌ 不需要 | 简单分支模式 |
| 知识库用用户原始输入检索 | ❌ 不需要 | 简单分支模式 |
| 下游 LLM 引用完整输出作上下文 | ❌ 不需要 | 直接引用 `llm_xxx.output` |
| Tool/API 需要 province、city 等独立参数 | ✅ 需要 | Code 守卫模式 |
| 需要组合多字段计算决策标志 | ✅ 需要 | Code 守卫模式 |

### 模式 A：简单分支模式（无 Code 节点，推荐用于纯意图路由）

当 Condition 只需判断意图类别，且下游不需要 JSON 子字段时，**不要使用 Code 节点**：

```
Input → LLM(意图分析, 输出纯文本意图标签如 "policy_query")
      → Condition(对 llm_xxx.output 做 contains 匹配)
        ├─ contains "policy"  → KB(user_input检索) → LLM(政策解读, output_user=true) → Input
        ├─ contains "company" → LLM(企业相关回答, output_user=true) → Input
        └─ right_handle(兜底) → LLM(通用回答, output_user=true) → Input
```

**关键要点**：
1. 意图分析 LLM 只需输出**纯文本意图标签**（如 `policy_query`），不需要输出 JSON
2. Condition 用 `contains` 匹配 LLM 输出文本
3. 知识库检索的 `user_question` 直接引用 `input_xxx.user_input`

### 模式 B：Code 守卫模式（当 Tool/API 需要独立子字段时）

当 LLM 输出结构化 JSON，且 **Tool/API 节点的参数需要其中的独立字段**时，采用此模式：

```
LLM(输出JSON字符串)
  → Code(容错解析 + 字段提取 + 决策标志)
    → Condition(检查 parse_ok + 业务标志)
      ├─ 满足条件 → Tool(使用 code_xxx.province/city 等独立参数)
      │            → LLM(结果整理, output_user=true) → Input
      └─ 不满足(兜底) → LLM(引导用户补充信息, output_user=true) → Input
```

**为什么需要条件守卫节点**：
1. 代码节点解析失败时（`parse_ok=false`），不应继续调用工具/API，应走兜底分支
2. 关键字段为空时（如省市区全空），工具调用无意义，应引导用户补充
3. 毕升条件节点表达能力有限（单分支只支持 AND 或 OR），复杂判断应在代码节点中计算为简单的 `"true"/"false"` 标志

**工具调用前的三件套（仅模式 B 适用）**：

| 策略 | 实现方式 | 说明 |
|------|---------|------|
| **断言（Assert）** | Code 节点输出 `parse_ok` / `should_query` 等标志 | 验证数据完整性 |
| **守卫（Guard）** | Condition 节点检查标志字段，不满足则拦截 | 阻止无效数据流入工具节点 |
| **降级（Fallback）** | 兜底分支连接引导 LLM（`output_user=true`） | 提示用户补充信息 |

### 完整示例（模式 B）

假设 LLM 意图分析输出 `{"intent": "company_query", "province": "广东", "city": "深圳"}`，**工具需要 province、city 作为独立参数**，工作流应为：

```
Input → LLM(意图分析, 输出JSON)
      → Code(解析JSON, 输出 intent/province/city/parse_ok/should_query)
      → Condition
        ├─ should_query contains "true"
        │   → Tool(企业查询, 使用 code_xxx.province/city)
        │   → LLM(结果整理, output_user=true) → Input
        ├─ intent contains "policy"
        │   → KB(知识库检索, user_question=input_xxx.user_input)
        │   → LLM(政策解读, output_user=true) → Input
        └─ right_handle(兜底: 解析失败/信息不足)
            → LLM(引导补充, output_user=true) → Input
```

---

## Edges 边连接

### 基本结构
```json
{
  "id": "xy-edge__源节点 ID 源句柄 - 目标节点 ID 目标句柄",
  "type": "customEdge",
  "source": "源节点 ID",
  "target": "目标节点 ID",
  "sourceHandle": "right_handle",
  "targetHandle": "left_handle",
  "animated": true
}
```

### 连接规则

**并行与汇聚**：
1. **支持并行 Fan-out**：任意节点可以有多条出边（从同一个 `right_handle`），下游节点会并行执行。例如 Input 同时连接 Tool 和 LLM，两者并行运行
2. **支持汇聚 Fan-in**：一个节点可以有多条入边。引擎会等待所有并行上游分支完成后再执行该节点
3. **⚠️ 禁止死分支**：并行分支中的**每个节点都必须有出边**。如果某个并行分支没有出边（死胡同），fan-in 汇聚节点会因等不到该分支完成而导致工作流卡死或异常结束。创建工具节点后，其 output 必须被下游 LLM 节点引用

**条件分支**：
4. **条件分支**：Condition 节点通过不同 sourceHandle（分支 ID）引出互斥边，运行时只执行匹配的分支
5. **⚠️ 条件分支禁止汇聚**：条件分支是互斥的（运行时只有一个分支执行），**严禁**多个互斥分支汇聚到同一个下游节点——未执行分支不会产生输出，汇聚节点会因等待未完成的上游而**卡死**。每个条件分支必须独立闭环（各自 LLM 设 `output_user=true` 连回 Input）

**循环与多轮对话**：
6. **成环/循环**：支持。多轮对话场景下，末端 LLM 节点（`output_user=true`）连回 Input 形成循环
7. **Output→Input 循环边**：使用 Output 节点输出时，必须包含 Output→Input 循环边；默认必需（多轮对话），除非用户明确要求单次执行

## Position 节点布局

### 核心规则

**节点宽度固定（334px），高度动态变化**

**水平布局**：
- 列间距：**834px**（节点宽度 334 + 安全间距 500）
- 起始 X：**-200**
- 每列递增：834px

**垂直布局**：
- 最小垂直间距：**100px**（节点下边缘到下一节点上边缘）
- 分支间垂直距离：**≥600px**

**对齐规则**：
1. 主干流程节点中心对齐
2. 同一分支的节点 Y 坐标一致
3. Condition 节点居中布置

**示例**：
```
Start(-200, 0) → Input(634, 382) → LLM(1468, 109) → Output(2302, 300)
```

---

### 分支布局规则（重要）

#### 平行分支布局

当工作流包含**多个平行分支**时（如条件分支场景），按以下规则布局：

**Y 坐标分配**：
- 第一个分支 Y 坐标：**109**
- 第二个分支 Y 坐标：**882**（+773px）
- 第三个分支 Y 坐标：**1655**（再 +773px）
- 分支间垂直距离：**≥600px**（推荐 773px）

**Condition 节点位置**：
- X 坐标：上一个节点 X + 834
- Y 坐标：所有分支 Y 坐标的**平均值**（居中布置）

**Output 节点位置**：
- X 坐标：分支节点 X + 834
- Y 坐标：与 Condition 节点相同（居中汇合）

#### 布局示例（3 分支）

```
                          ┌─ LLM_Travel (y=109) ──┐
                          │                        │
Condition (y=500) ────────┼─ LLM_Doc (y=882) ──────┼──→ Output (y=500)
                          │                        │
                          └─ LLM_General (y=1655) ─┘
```

**详细坐标**：
```
Start:      (-200, 282)
Input:      (634, 382)
LLM_Intent: (1468, 109)
Condition:  (2302, 500)   ← 居中：(109 + 882 + 1655) / 3 ≈ 882

分支节点：
- LLM_Travel:   (3136, 109)
- LLM_Doc:      (3136, 882)
- LLM_General:  (3136, 1655)

Output:     (3970, 500)   ← 与 Condition 对齐
```

#### 布局示例（2 分支）

```
                    ┌─ LLM_Branch_A (y=109) ─┐
Condition (y=500) ─┤                         ├→ Output (y=500)
                    └─ LLM_Branch_B (y=882) ─┘
```

**详细坐标**：
```
Condition:  (2302, 500)   ← 居中：(109 + 882) / 2 ≈ 500

分支节点：
- LLM_A: (3136, 109)
- LLM_B: (3136, 882)

Output:     (3970, 500)   ← 与 Condition 对齐
```

#### 布局计算技巧

1. **确定分支数量**：n 个分支
2. **计算 Condition Y 坐标**：(第一个分支 Y + 最后一个分支 Y) / 2
3. **Output Y 坐标**：与 Condition 相同
4. **分支节点 X 坐标**：Condition X + 834
5. **Output X 坐标**：分支节点 X + 834

**通用公式**：
```python
# 假设有 n 个分支
branch_y_coords = [109 + i * 773 for i in range(n)]  # [109, 882, 1655, ...]
condition_y = (branch_y_coords[0] + branch_y_coords[-1]) / 2
output_y = condition_y
```

---

## 注意事项

### 必须遵守的规则

1. **唯一 ID 生成**: `类型_随机后缀`（如 `start_654ad`）
2. **data.id**: 必须与外层 id 一致
3. **data.description**: 每个节点必需
4. **position 和 measured**: 每个节点必需（否则导入报错）
5. **变量引用格式**: `{{#节点 ID.变量名#}}`（注意 `#` 符号）
6. **禁止引用 LLM 输出的子属性**: `{{#llm_xxx.output.字段名#}}` 无效！如需子字段，通过 Code 节点解析后引用 `{{#code_xxx.字段名#}}`
7. **Code 节点按需使用，不可滥用**: 仅当下游 Tool/API 需要 LLM JSON 输出的独立子字段作为参数时才用 Code 节点；纯意图路由（Condition `contains` 匹配）不需要 Code 节点
8. **边连接完整**: 所有节点必须正确连接，禁止出现无出边的死分支节点（会导致工作流卡死）
9. **条件分支**: sourceHandle 必须与条件 ID 对应；**条件分支互斥，严禁多个分支汇聚到同一下游节点**（会卡死），每个分支独立闭环
10. **knowledge 字段**: 必须使用嵌套结构
11. **knowledge_retriever 输出引用**: 下游用 `{{#knowledge_xxx.retrieved_output#}}`（内层 value 的 key），**不是** `{{#knowledge_xxx.retrieved_result#}}`（外层组 key）
12. **output 字段**: 必须包含 `global` 映射函数
13. **Tool 节点**: 参数值引用用户输入时使用 `{{#input_xxx.user_input#}}`；`tool_key` 必须与上下文提供的值完全一致（MCP 工具包含 `_数字ID` 后缀）
14. **Output 节点**: message 必须引用最终的 LLM 输出
15. **Code 节点代码必须容错**: 使用 Code 节点时，`json.loads` 等操作必须 try-except，返回安全默认值；必须输出 `parse_ok` 等决策标志
16. **工具调用前必须有条件守卫**: 当 Tool/MCP 节点的参数依赖 Code 节点解析结果时，Code 和 Tool 之间必须插入 Condition 节点，检查数据有效性后再调用

### 常见错误

- ❌ 缺少 `position` 或 `measured` → ✅ 每个节点必须包含
- ❌ `data.id` 与外层 `id` 不一致 → ✅ 必须一致
- ❌ 缺少 `data.description` → ✅ 每个节点必需
- ❌ `{{节点 ID.变量}}` → ✅ `{{#节点 ID.变量#}}`
- ❌ `{{#llm_xxx.output.city#}}`（引用 LLM 子属性）→ ✅ 插入 Code 节点解析后引用 `{{#code_xxx.city#}}`
- ❌ 编造 `weather_query` → ✅ 使用上下文提供的工具或内置 `web_search`
- ❌ MCP 工具 `tool_key` 截断数字后缀（如写成 `get-stations-code-in-city`）→ ✅ 必须完整保留 `get-stations-code-in-city_28785811`
- ❌ knowledge 字段缺少 type → ✅ `{"type": "knowledge", "value": [...]}`
- ❌ 节点 `data.id` 与外层 `id` 不完全一致（如外层 `tool_realtime_abc`，内层写成 `tool_abc`）→ ✅ 两者必须逐字符相同
- ❌ LLM `tab.options` 含 `help: "true"` → ✅ options 只含 `key` 和 `label`
- ❌ LLM `batch_variable` 放在输出分组 → ✅ 放在第一个无名分组
- ❌ LLM 提示词分组缺少 `image_prompt` → ✅ 必须包含
- ❌ Code 节点裸调用 `json.loads` 无 try-except → ✅ 必须容错，返回安全默认值
- ❌ Code 节点缺少 `parse_ok` 决策标志 → ✅ 必须输出，供下游条件节点判断
- ❌ Code 解析出的关键字段全空仍调用工具 → ✅ 必须用 Condition 守卫拦截，走兜底分支引导用户
- ❌ knowledge_retriever `v` 写成 `"2"` 字符串 → ✅ 必须是整数 `2`
- ❌ Input 节点 group_params 只有接收文本 → ✅ 必须包含全部 4 个分组
- ❌ Input `description` 写成简化版 → ✅ 必须是 `"接收用户在会话页面的输入，支持 2 种形式：对话框输入，表单输入。"`
- ❌ 并行分支中某个工具节点没有出边（死分支）→ ✅ 每个并行分支的节点都必须有出边连到下游，工具节点的 output 必须被后续 LLM 节点引用，否则 fan-in 汇聚会导致工作流卡死
- ❌ 条件分支的多个下游节点汇聚到同一个 Output 或 LLM 节点 → ✅ 每个条件分支独立闭环（各自 LLM `output_user=true` 连回 Input），互斥分支汇聚会导致流程卡死
- ❌ 下游引用知识库检索输出用 `{{#knowledge_xxx.retrieved_result#}}`（外层组 key）→ ✅ 必须用 `{{#knowledge_xxx.retrieved_output#}}`（内层变量 key）
- ❌ 纯意图路由场景也用 Code 节点解析 JSON → ✅ Condition 用 `contains` 直接匹配 LLM 文本输出即可，不需要 Code 节点

---

## 输出格式

生成的 JSON 文件必须是完整的、可直接导入毕昇平台的格式：

**重要原则**：
1. **输出即可用**：生成的 JSON 必须可以直接导入毕昇平台并正常工作
2. **默认多轮对话**：除非用户明确要求单次执行，否则必须包含 Output→Input 循环边
3. **字段完整**：所有必需字段（position、measured、description 等）必须包含

---

## 质量标准

### 合格标准（必达）

- JSON 格式正确，可以被解析
- 包含完整的 nodes、edges 配置
- 至少包含 start、input、output 节点
- 节点间有正确的连接关系，无死分支（每个节点都有出边，或是末端循环回 Input 的 LLM 节点）
- 变量引用格式正确
- 所有必填字段完整（包括 position、measured、description）
- 布局合理，节点不重叠

### 优秀标准（建议）

- 提示词设计专业，符合业务需求
- 节点布局美观，逻辑清晰
- 包含适当的条件分支处理
- 支持知识库检索功能
- 包含开场引导和预设问题
- 变量命名语义化
- 根据场景选择正确模式：纯意图路由用简单分支模式（无 Code），Tool 需子字段时用 Code 守卫模式
- 使用 Code 节点时，代码带容错和决策标志
- Tool/API 调用前有 Condition 守卫节点，数据无效时走兜底分支

---

## 示例工作流

- 多分支意图识别工作流（无工具调用）：参考 `examples/personal-travel-assistant.json`
- LLM→Code→Condition→Tool 模式的完整工作流（含代码节点 + 条件守卫）：参考 `examples/code-guard-tool-pattern.json`

