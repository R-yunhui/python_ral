# 毕昇工作流节点完整 JSON 示例

生成工作流时读取本文件获取各节点的完整 JSON 结构。

## 目录

1. [Start 开始节点](#1-start-开始节点)
2. [Input 输入节点](#2-input-输入节点)
3. [LLM 节点](#3-llm-节点)
4. [Knowledge Retriever 知识库检索节点](#4-knowledge-retriever-知识库检索节点)
5. [Tool 工具节点](#5-tool-工具节点)
6. [Output 输出节点](#6-output-输出节点)
7. [Condition 条件判断节点](#7-condition-条件判断节点)
8. [Code 代码节点](#8-code-代码节点)

---

## 1. Start 开始节点

包含两个分组：开场引导（`guide_word` + `guide_question`）、全局变量（5 个字段缺一不可）。

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

**`preset_question` 格式**：value 必须是对象数组 `[{"key": "pq_001", "value": "问题文本"}]`，不是纯字符串数组。

---

## 2. Input 输入节点

必须包含 4 个分组（接收文本、文件上传、推荐问题、表单输入），`description` 固定不变。

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

---

## 3. LLM 节点

**group_params 严格顺序**：① 无名分组(batch_variable) → ② 模型设置 → ③ 提示词 → ④ 输出

**注意**：`tab.options` 只含 `key` 和 `label`，**不含 `help`**（与 Input 节点不同）。

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

**变量引用格式**：`{{#节点ID.变量名#}}`，需同时添加 `varZh` 中文映射。

---

## 4. Knowledge Retriever 知识库检索节点

**⚠️ `v` 为整数 `2`（不是字符串 `"2"`）**。下游引用输出时用内层 key `retrieved_output`。

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

**下游引用**：✅ `{{#knowledge_xxx.retrieved_output#}}` ❌ `{{#knowledge_xxx.retrieved_result#}}`

---

## 5. Tool 工具节点

### 内置工具（web_search）

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

### MCP 工具

`tool_key` 必须完整保留 `_数字ID` 后缀。MCP 参数含 `desc` 字段。

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

---

## 6. Output 输出节点

仅在需要输出文件、表单、富文本时使用。纯文本回答用 LLM 的 `output_user=true` 流式输出。

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

---

## 7. Condition 条件判断节点

`value` 数组只放有实际条件的分支，兜底用 `right_handle` 出边。

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

**对应出边**（含 right_handle 兜底）：
```json
{"source": "condition_xxx", "sourceHandle": "branch_a",     "target": "llm_a_xxx"},
{"source": "condition_xxx", "sourceHandle": "branch_b",     "target": "llm_b_xxx"},
{"source": "condition_xxx", "sourceHandle": "right_handle", "target": "llm_default_xxx"}
```

**出边规则**：有条件分支 sourceHandle = 分支 `id`，兜底 sourceHandle = `"right_handle"`。

---

## 8. Code 代码节点

**group_params 顺序**：① 入参 → ② 执行代码 → ③ 出参

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

### 简单 JSON 解析模板

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

**字段说明**：
- `code_input.value`：每项含 `key`（参数名）、`type`（`"ref"`）、`label`（中文说明）、`value`（上游路径如 `"llm_xxx.output"`）
- `code_output.value`：每项含 `key`（字段名，对应 return dict 的键）、`type`（`"str"` / `"int"` / `"float"` / `"bool"` / `"list"` / `"dict"`）
- `code_output` 必须包含 `global` 映射：`"code:value.map(el => ({ label: el.key, value: el.key }))"`
