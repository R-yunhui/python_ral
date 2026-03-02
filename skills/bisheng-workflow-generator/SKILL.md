---
name: bisheng-workflow-generator
description: 专业的毕昇 (BiSheng) 工作流 JSON 文件生成器，根据用户业务需求自动生成完整的毕昇工作流配置文件，支持各种节点类型和复杂工作流逻辑。当用户提到毕昇、bisheng、毕升工作流时自动触发。
---

# 毕昇 (BiSheng) 工作流生成器

专业的毕昇工作流 JSON 文件自动生成工具，能够根据用户的业务需求自动生成符合毕昇平台规范的工作流配置文件。

## 核心功能

- **完整工作流生成**: 自动生成包含 nodes、edges 的完整 JSON 文件
- **多节点支持**: 支持 start、input、output、llm、condition、knowledge_retriever、tool、code、rag 等所有节点类型
- **智能连接**: 自动生成节点间的 edges 连接关系
- **参数配置**: 智能推荐模型参数、提示词配置
- **规范格式**: 严格遵循毕昇工作流 JSON 规范
- **动态布局**: 根据节点实际高度动态计算布局，避免节点重叠

## 使用方法

### 基础用法

```
生成一个毕昇工作流用于 [业务需求描述]
```

### 详细用法

```
帮我生成一个毕昇工作流:
- 功能：[工作流要实现的功能]
- 输入：[用户输入的内容]
- 处理步骤：[详细的处理逻辑]
- 输出：[期望的输出结果]
- 知识库：[需要的知识库，可选]
```

## 毕昇工作流 JSON 结构

### 顶层结构

```json
{
  "status": 2,
  "user_id": 1,
  "description": "工作流描述",
  "guide_word": null,
  "update_time": "2026-01-01T00:00:00",
  "name": "工作流名称",
  "logo": "",
  "flow_type": 10,
  "create_time": "2026-01-01T00:00:00",
  "id": "工作流唯一 ID（32 位）",
  "nodes": [],
  "edges": [],
  "viewport": {"x": 0, "y": 0, "zoom": 1}
}
```

**字段说明:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | int | 状态，2 表示已发布 |
| `flow_type` | int | 工作流类型，10 为标准工作流 |
| `id` | string | 32 位唯一 ID，可使用 UUID |
| `nodes` | array | 节点列表 |
| `edges` | array | 边连接列表 |
| `viewport` | object | 画布视图配置 |

## 节点类型

毕昇支持以下节点类型：

| 类型 | 说明 | 必需 |
|------|------|------|
| `start` | 开始节点 | 是 |
| `input` | 输入节点 | 是 |
| `output` | 输出节点 | 是 |
| `llm` | 大语言模型节点 | 否 |
| `condition` | 条件判断节点 | 否 |
| `knowledge_retriever` | 知识库检索节点 | 否 |
| `rag` | RAG 检索节点 | 否 |
| `tool` | 工具节点 | 否 |
| `code` | 代码执行节点 | 否 |
| `agent` | Agent 节点 | 否 |
| `report` | 报告节点 | 否 |

## 节点结构详解

### 通用节点结构

每个节点包含以下关键字段：

```json
{
  "id": "节点唯一 ID",
  "data": {
    "v": "版本号",
    "id": "节点 ID",
    "name": "节点名称",
    "type": "节点类型",
    "description": "节点描述",
    "group_params": [],
    "tab": {}
  },
  "type": "flowNode",
  "position": {"x": 100, "y": 200},
  "measured": {
    "width": 334,
    "height": 500
  }
}
```

**ID 命名规范:** 节点 ID 格式为 `类型_随机后缀`，如 `start_654ad`、`llm_ad8b7`

**字段说明:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 节点唯一 ID |
| `data.v` | string | 节点版本 |
| `data.name` | string | 节点显示名称 |
| `data.type` | string | 节点类型 |
| `data.group_params` | array | 节点参数分组 |
| `data.tab` | object | tab 切换配置 |
| `position` | object | 节点在画布上的位置 |
| `measured` | object | 节点尺寸 |

### Start 开始节点

开始节点是工作流的起始点，包含开场引导和全局变量。

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
          {
            "key": "guide_word",
            "type": "textarea",
            "label": "开场白",
            "value": ""
          },
          {
            "key": "guide_question",
            "type": "input_list",
            "label": "引导问题",
            "value": ["问题 1", "问题 2", "问题 3"]
          }
        ]
      },
      {
        "name": "全局变量",
        "params": [
          {
            "key": "user_info",
            "type": "var",
            "label": "用户信息",
            "value": "",
            "global": "key"
          },
          {
            "key": "current_time",
            "type": "var",
            "label": "当前时间",
            "value": "",
            "global": "key"
          },
          {
            "key": "chat_history",
            "type": "chat_history_num",
            "value": 10,
            "global": "key"
          },
          {
            "key": "preset_question",
            "type": "input_list",
            "label": "预设问题",
            "value": [
              {"key": "id1", "value": "预设问题 1"},
              {"key": "id2", "value": "预设问题 2"}
            ],
            "global": "item:input_list"
          },
          {
            "key": "custom_variables",
            "type": "global_var",
            "label": "自定义变量",
            "value": [],
            "global": "item:input_list"
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": -200, "y": 0},
  "measured": {"width": 334, "height": 1033}
}
```

**参数类型说明:**

| 类型 | 说明 |
|------|------|
| `textarea` | 多行文本 |
| `input_list` | 输入列表 |
| `var` | 变量 |
| `chat_history_num` | 聊天历史数量 |
| `global_var` | 全局变量 |

**输出变量:**

- `user_info`: 用户信息
- `current_time`: 当前时间
- `chat_history`: 聊天历史
- `preset_question`: 预设问题

### Input 输入节点

输入节点接收用户输入，支持对话框输入和表单输入两种模式。

```json
{
  "id": "input_1efc6",
  "data": {
    "v": "3",
    "id": "input_1efc6",
    "tab": {
      "value": "dialog_input",
      "options": [
        {"key": "dialog_input", "label": "对话框输入"},
        {"key": "form_input", "label": "表单输入"}
      ]
    },
    "name": "输入",
    "type": "input",
    "description": "接收用户在会话页面的输入。",
    "group_params": [
      {
        "name": "接收文本",
        "params": [
          {
            "key": "user_input",
            "tab": "dialog_input",
            "type": "var",
            "label": "用户输入",
            "global": "key"
          }
        ]
      },
      {
        "params": [
          {
            "key": "user_input_file",
            "tab": "dialog_input",
            "value": false
          },
          {
            "key": "dialog_files_content",
            "tab": "dialog_input",
            "type": "var",
            "global": "key"
          },
          {
            "key": "dialog_file_accept",
            "tab": "dialog_input",
            "type": "select_fileaccept",
            "value": "file"
          },
          {
            "key": "dialog_image_files",
            "tab": "dialog_input",
            "type": "var",
            "global": "key"
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 634, "y": 382},
  "measured": {"width": 334, "height": 268}
}
```

**tab 模式说明:**

| 模式 | 说明 |
|------|------|
| `dialog_input` | 对话框输入模式 |
| `form_input` | 表单输入模式 |

**输出变量:**

- `user_input`: 用户输入的文本
- `dialog_files_content`: 上传文件的内容
- `dialog_image_files`: 上传的图片文件

### LLM 大语言模型节点

LLM 节点调用大模型处理任务，是最常用的节点类型。

```json
{
  "id": "llm_ad8b7",
  "data": {
    "v": "2",
    "id": "llm_ad8b7",
    "tab": {
      "value": "single",
      "options": [
        {"key": "single", "label": "单次执行"},
        {"key": "batch", "label": "批量执行"}
      ]
    },
    "name": "LLM 节点",
    "type": "llm",
    "description": "调用大模型回答用户问题或者处理任务。",
    "group_params": [
      {
        "params": [
          {
            "key": "batch_variable",
            "tab": "batch",
            "type": "user_question",
            "value": []
          }
        ]
      },
      {
        "name": "模型设置",
        "params": [
          {
            "key": "model_id",
            "type": "bisheng_model",
            "label": "模型",
            "value": 5,
            "required": true
          },
          {
            "key": "temperature",
            "type": "slide",
            "label": "温度",
            "step": 0.1,
            "scope": [0, 2],
            "value": 0.7
          }
        ]
      },
      {
        "name": "提示词",
        "params": [
          {
            "key": "system_prompt",
            "type": "var_textarea",
            "label": "系统提示词",
            "value": "你是一个专业的 AI 助手。"
          },
          {
            "key": "user_prompt",
            "type": "var_textarea",
            "label": "用户提示词",
            "value": "用户输入：{{#input_1efc6.user_input#}}",
            "required": true
          },
          {
            "key": "image_prompt",
            "type": "image_prompt",
            "value": []
          }
        ]
      },
      {
        "name": "输出",
        "params": [
          {
            "key": "output_user",
            "type": "switch",
            "label": "输出给用户",
            "value": true
          },
          {
            "key": "output",
            "type": "var",
            "value": []
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 1468, "y": 109},
  "measured": {"width": 334, "height": 816}
}
```

**变量引用格式:**

使用 `{{#节点 ID.变量名#}}` 引用其他节点的输出：

```json
{
  "key": "user_prompt",
  "value": "用户输入：{{#input_1efc6.user_input#}}\n检索结果：{{#knowledge_retriever_834c6.retrieved_output#}}",
  "varZh": {
    "input_1efc6.user_input": "输入/user_input",
    "knowledge_retriever_834c6.retrieved_output": "知识库检索/retrieved_output"
  }
}
```

**tab 模式说明:**

| 模式 | 说明 |
|------|------|
| `single` | 单次执行 |
| `batch` | 批量执行（需配置 batch_variable） |

**输出变量:**

- `output`: LLM 生成的输出文本

### Knowledge Retriever 知识库检索节点

知识库检索节点从指定的知识库中检索相关内容。

```json
{
  "id": "knowledge_retriever_834c6",
  "data": {
    "v": 2,
    "id": "knowledge_retriever_834c6",
    "name": "知识库检索",
    "type": "knowledge_retriever",
    "description": "根据用户问题从知识库中检索相关内容。",
    "group_params": [
      {
        "name": "知识库检索设置",
        "params": [
          {
            "key": "user_question",
            "type": "user_question",
            "label": "检索问题",
            "value": ["llm_afcdd.output"],
            "varZh": {"llm_afcdd.output": "上游节点/output"},
            "required": true
          },
          {
            "key": "knowledge",
            "type": "knowledge_select_multi",
            "label": "知识库",
            "value": {
              "type": "knowledge",
              "value": [{"key": 6, "label": "知识库名称"}]
            },
            "required": true
          },
          {
            "key": "metadata_filter",
            "type": "metadata_filter",
            "value": {"enabled": false}
          },
          {
            "key": "advanced_retrieval_switch",
            "type": "search_switch",
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
            "value": [{"key": "retrieved_output", "label": "检索结果"}]
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 3970, "y": -800},
  "measured": {"width": 334, "height": 135}
}
```

**检索配置说明:**

| 参数 | 说明 |
|------|------|
| `user_question` | 检索问题，引用上游节点的输出（数组格式：`["节点 ID.变量名"]`） |
| `knowledge` | 知识库配置，`key` 是知识库 ID（整数），`label` 是知识库名称 |
| `keyword_weight` | 关键词检索权重（0-1） |
| `vector_weight` | 向量检索权重（0-1） |
| `rerank_flag` | 是否启用重排序 |

**知识库配置示例:**
```json
{
  "key": "knowledge",
  "type": "knowledge_select_multi",
  "value": {
    "type": "knowledge",
    "value": [
      {"key": 1, "label": "招商引资相关政策"},
      {"key": 2, "label": "深汕海洋产业"}
    ]
  }
}
```

**重要提示：** `key` 字段是知识库的 ID（必须是整数），需要向用户确认或使用占位值并提示用户修改。

**输出变量:**

- `retrieved_output`: 检索到的文档内容

### Condition 条件判断节点

条件节点根据条件表达式执行不同的分支。

```json
{
  "id": "condition_e3478",
  "data": {
    "v": "1",
    "id": "condition_e3478",
    "name": "条件分支",
    "type": "condition",
    "description": "根据条件表达式执行不同的分支。",
    "group_params": [
      {
        "params": [
          {
            "key": "condition",
            "type": "condition",
            "value": [
              {
                "id": "5d8602bc",
                "operator": "or",
                "conditions": [
                  {
                    "id": "eda4718b",
                    "left_var": "llm_ad8b7.output",
                    "left_label": "意图识别/output",
                    "right_value": "A",
                    "right_value_type": "input",
                    "comparison_operation": "equals"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 2302, "y": 500},
  "measured": {"width": 322, "height": 232}
}
```

**比较运算符:**

| 运算符 | 说明 |
|--------|------|
| `equals` | 等于 |
| `not_equals` | 不等于 |
| `contains` | 包含 |
| `not_contains` | 不包含 |
| `is_empty` | 为空 |
| `is_not_empty` | 不为空 |
| `greater_than` | 大于 |
| `less_than` | 小于 |

**逻辑运算符:**

- `and`: 所有条件都满足
- `or`: 任一条件满足

**分支连接:** 条件节点的分支边使用条件 ID 作为 sourceHandle

### Tool 工具节点

工具节点调用外部工具或 API。

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
          {
            "key": "query",
            "type": "var_textarea",
            "label": "query",
            "value": "{{#input_1efc6.user_input#}}",
            "required": true
          }
        ]
      },
      {
        "name": "输出",
        "params": [
          {
            "key": "output",
            "type": "var",
            "label": "输出变量",
            "global": "key"
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 6472, "y": -600},
  "measured": {"width": 334, "height": 410}
}
```

**常用工具:**

| tool_key | 说明 |
|----------|------|
| `web_search` | 联网搜索 |
| `http_request` | HTTP 请求 |

### Output 输出节点

输出节点向用户发送文本和文件。

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
          {
            "key": "message",
            "type": "var_textarea_file",
            "label": "输出内容",
            "value": {
              "msg": "{{#llm_final.output#}}",
              "files": []
            },
            "varZh": {"llm_final.output": "最终回答/output"},
            "required": true
          },
          {
            "key": "output_result",
            "type": "output_form",
            "label": "用户输入内容",
            "value": {"type": "", "value": ""}
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 8974, "y": 533},
  "measured": {"width": 334, "height": 433}
}
```

**message 字段说明:**

| 字段 | 说明 |
|------|------|
| `msg` | 输出的文本内容 |
| `files` | 输出的文件列表 |

### Code 代码执行节点

代码节点执行 Python 代码。

```json
{
  "id": "code_a1b2c",
  "data": {
    "v": "1",
    "id": "code_a1b2c",
    "name": "代码执行",
    "type": "code",
    "description": "执行 Python 代码。",
    "group_params": [
      {
        "name": "输入",
        "params": [
          {
            "key": "code_input",
            "value": [
              {"key": "input_var", "type": "ref", "value": "input_1efc6.user_input"}
            ]
          }
        ]
      },
      {
        "name": "代码",
        "params": [
          {
            "key": "code",
            "value": "def main(input_var: str) -> dict:\n    return {\"result\": input_var}"
          }
        ]
      },
      {
        "name": "输出",
        "params": [
          {
            "key": "code_output",
            "value": [{"key": "result", "type": "string"}]
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 1600, "y": 282},
  "measured": {"width": 334, "height": 500}
}
```

**代码格式要求:**

- 入口函数必须为 `main`
- 返回值必须是 `dict` 类型
- 输出变量需要在 `code_output` 中定义

### RAG 节点

RAG 节点结合检索和生成，自动完成知识库检索和回答生成。

```json
{
  "id": "rag_7a8b9",
  "data": {
    "v": "1",
    "id": "rag_7a8b9",
    "name": "RAG 检索",
    "type": "rag",
    "description": "根据用户问题检索知识库并生成回答。",
    "group_params": [
      {
        "name": "模型设置",
        "params": [
          {"key": "model_id", "type": "bisheng_model", "value": 5}
        ]
      },
      {
        "name": "提示词",
        "params": [
          {"key": "system_prompt", "type": "var_textarea", "value": "根据知识库内容回答问题。"},
          {"key": "user_prompt", "type": "var_textarea", "value": "{{#input_1efc6.user_input#}}"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 1200, "y": 282}
}
```

## Edges 边连接

边定义节点之间的连接关系。

### 基本边结构

```json
{
  "id": "xy-edge__start_654adright_handle-input_1efc6left_handle",
  "type": "customEdge",
  "source": "start_654ad",
  "target": "input_1efc6",
  "sourceHandle": "right_handle",
  "targetHandle": "left_handle",
  "animated": true
}
```

**字段说明:**

| 字段 | 说明 |
|------|------|
| `id` | 边的唯一 ID，格式：`xy-edge__源节点 ID 源句柄 - 目标节点 ID 目标句柄` |
| `source` | 源节点 ID |
| `target` | 目标节点 ID |
| `sourceHandle` | 源节点的连接点，通常为 `right_handle` |
| `targetHandle` | 目标节点的连接点，通常为 `left_handle` |
| `animated` | 是否显示动画效果 |

### 标准连接示例

```json
{
  "id": "xy-edge__input_1efc6right_handle-llm_ad8b7left_handle",
  "type": "customEdge",
  "source": "input_1efc6",
  "target": "llm_ad8b7",
  "sourceHandle": "right_handle",
  "targetHandle": "left_handle",
  "animated": true
}
```

### 条件分支边

条件节点的分支边使用条件 ID 作为 sourceHandle：

```json
{
  "id": "xy-edge__condition_e34785d8602bc-llm_b9869left_handle",
  "type": "customEdge",
  "source": "condition_e3478",
  "target": "llm_b9869",
  "sourceHandle": "5d8602bc",
  "targetHandle": "left_handle",
  "animated": true
}
```

**注意:** `sourceHandle` 的值 `5d8602bc` 是条件节点中 `condition.value[0].id`

### 默认分支边

条件节点的默认分支使用 `right_handle`：

```json
{
  "id": "xy-edge__condition_e3478right_handle-llm_593c1left_handle",
  "type": "customEdge",
  "source": "condition_e3478",
  "target": "llm_593c1",
  "sourceHandle": "right_handle",
  "targetHandle": "left_handle",
  "animated": true
}
```

### 循环连接（输出回到输入）

```json
{
  "id": "xy-edge__output_5b20bright_handle-input_1efc6left_handle",
  "type": "customEdge",
  "source": "output_5b20b",
  "target": "input_1efc6",
  "sourceHandle": "right_handle",
  "targetHandle": "left_handle",
  "animated": true
}
```

### 连接规则

1. 每个节点至多有一个入边（start 节点除外）
2. 节点可以有多个出边（condition 等分支节点）
3. 最终必须连接到 output 节点
4. 条件分支的 sourceHandle 必须与条件 ID 对应

## Position 节点布局

### 核心布局原则

**重要：** 节点宽度固定，高度动态变化，必须根据实际高度计算布局！

| 节点类型 | 宽度 (px) | 高度范围 (px) | 说明 |
|---------|----------|------------|------|
| start | 334 | 600-1100 | 包含开场引导和全局变量，高度可变 |
| input | 334 | 268-500 | 对话框输入较矮，表单输入较高 |
| llm | 334 | 700-850 | 包含提示词配置，高度较大 |
| knowledge_retriever | 334 | 135-600 | 基础检索较矮，高级配置较高 |
| condition | 322 | 232-400 | 条件分支节点，宽度略窄 |
| tool | 334 | 410-500 | 工具节点中等高度 |
| output | 334 | 433-500 | 输出节点中等高度 |
| code | 334 | 500-700 | 代码节点高度可变 |

### 推荐布局规则

**水平间距（关键）：**
- 列间距 = 节点宽度 (334) + 安全间距 (500) = **834px**
- 起始 X: **-200**（给左侧留空间）
- 每列递增：834px

**垂直间距（关键）：**
- 最小垂直间距：**100px**（节点下边缘到下一节点上边缘）
- 推荐垂直间距：**150-200px**（美观布局）
- 分支间垂直距离：**≥600px**（避免视觉拥挤）

**对齐规则：**
1. 主干流程节点中心对齐
2. 同一分支的节点保持 Y 坐标一致
3. 并行分支的节点按功能对齐
4. Condition 节点作为分支起点，居中布置

### 线性布局示例

```
Start(-200, 0) → Input(634, 382) → LLM(1468, 109) → Output(2302, 300)
```

### 分支布局示例（推荐）

```
主流程：Start → Input → 意图识别 → 条件分支

条件分支后：
                    海洋政策分支 (Y: -800)
                   /
条件节点 (Y: 500) —————— 招商引资分支 (Y: 200)
                   \
                    普通对话分支 (Y: 1200)

分支内节点布局：
- 同一分支的所有节点保持 Y 坐标一致
- 相邻列节点 X 间距：834px
- 分支间 Y 间距：≥600px（考虑节点高度后不重叠）
```

### 复杂布局示例（完整计算）

```
列 1: Start(-200, 0) [高度 1033]
列 2: Input(634, 382) [高度 268，与 Start 中心对齐]
列 3: 意图识别 (1468, 109) [高度 816，与 Input 中心对齐]
列 4: 条件分支 (2302, 500) [高度 232，作为分支起点]

列 5（分支）:
  - 海洋 Query(3136, -800) [高度 800]
  - 招商 Query(3136, 200) [高度 800]
  - 普通对话 (3136, 1200) [高度 800]

列 6（分支）:
  - 海洋知识 (3970, -800) [高度 135，与 Query 对齐]
  - 招商知识 (3970, 200) [高度 749，与 Query 对齐]

列 7（分支）:
  - 海洋判断 (4804, -800) [高度 135，与 knowledge 对齐]
  - 招商判断 (4804, 200) [高度 800，与 knowledge 对齐]

列 8（条件分支）:
  - 海洋条件 (5638, -800) [高度 232]
  - 招商条件 (5638, 200) [高度 232]

列 9（二次分支）:
  海洋分支：
    - 知识库回答 (6472, -1000) [高度 800]
    - 联网搜索 (6472, -600) [高度 410]
  
  招商分支：
    - 知识库回答 (6472, 0) [高度 800]
    - 联网搜索 (6472, 500) [高度 426]

列 10:
  - 海洋联网回答 (7306, -600) [高度 800]
  - 招商联网回答 (7306, 500) [高度 800]

列 11: 最终整合 (8140, 300) [高度 800，汇集所有分支]
列 12: 输出 (8974, 533) [高度 433，与 final 中心对齐]
```

### 布局验证清单

生成工作流时必须验证：
- [ ] 所有节点 X 坐标间隔 ≥ 500px（边缘到边缘）
- [ ] 同一列不同分支的节点 Y 坐标间隔 ≥ 100px（考虑高度后）
- [ ] 同一分支的节点 Y 坐标对齐
- [ ] Condition 节点的分支 sourceHandle 与条件 ID 对应
- [ ] 所有节点最终连接到输出节点
- [ ] viewport 配置合适（zoom: 0.5-0.6, x: 400, y: 300）

## 实际案例

### 案例 1: 知识库问答工作流

**需求**: 用户问题 → 知识库检索 → LLM 生成回答

**流程:**
```
开始 → 输入 → 知识库检索 → LLM 生成回答 → 输出
```

**关键配置:**

```json
// Knowledge Retriever 节点
{
  "key": "knowledge",
  "value": {
    "type": "knowledge",
    "value": [{"key": 6, "label": "招商政策知识库"}]
  }
}

// LLM 节点的 user_prompt
{
  "value": "用户问题：{{#input_1efc6.user_input#}}\n\n知识库检索结果：\n{{#knowledge_retriever_834c6.retrieved_output#}}"
}
```

### 案例 2: 意图识别 + 条件分支工作流

**需求**: 识别用户意图，根据不同意图走不同处理流程

**流程:**
```
开始 → 输入 → 意图识别 (LLM) → 条件分支
                              ├── 投资咨询 → 知识库检索 → LLM → 输出
                              └── 普通聊天 → LLM → 输出
```

**关键配置:**

```json
// 意图识别 LLM 的 system_prompt
{
  "value": "你是招商助手，判断用户意图。只输出 A 或 B。\nA. 投资咨询\nB. 普通聊天"
}

// 条件节点配置
{
  "condition": [{
    "id": "5d8602bc",
    "operator": "or",
    "conditions": [{
      "left_var": "llm_ad8b7.output",
      "right_value": "A",
      "comparison_operation": "equals"
    }]
  }]
}
```

### 案例 3: 联网搜索工作流

**需求**: 用户问题 → 联网搜索 → LLM 总结 → 输出

**流程:**
```
开始 → 输入 → 联网搜索 (Tool) → LLM 总结 → 输出
```

**关键配置:**

```json
// Tool 节点
{
  "tool_key": "web_search",
  "group_params": [{
    "params": [{"key": "query", "value": "{{#input_1efc6.user_input#}}"}]
  }]
}

// LLM 节点的 user_prompt
{
  "value": "用户问题：{{#input_1efc6.user_input#}}\n\n联网搜索结果：\n{{#tool_982ee.output#}}\n\n请根据搜索结果回答用户问题。"
}
```

### 案例 4: 知识库检索结果判断工作流

**需求**: 检索知识库，有结果则使用知识库回答，无结果则联网搜索

**流程:**
```
开始 → 输入 → LLM 生成 Query → 知识库检索 → LLM 判断结果 → 条件分支
                                                    ├── 有结果 → LLM 生成回答 → 输出
                                                    └── 无结果 → 联网搜索 → LLM 生成回答 → 输出
```

**关键配置:**

```json
// LLM 判断结果的 user_prompt
{
  "value": "检索结果：{{#knowledge_retriever_834c6.retrieved_output#}}\n\n判断是否有有效内容：\n- 有内容输出：{\"has_result\": true}\n- 无内容输出：{\"has_result\": false}"
}

// 条件节点配置
{
  "condition": [{
    "id": "584d237e",
    "operator": "and",
    "conditions": [{
      "left_var": "llm_86d4a.output",
      "right_value": "true",
      "comparison_operation": "contains"
    }]
  }]
}
```

## 常用提示词模板

### 意图识别

```
你是深汕招商助手，负责判断用户咨询意图。只输出 A 或 B，不要解释。

意图分类：
A. 投资咨询 - 询问政策、园区、产业配套、投资事宜等
B. 普通聊天 - 问候、闲聊、无关话题

严格输出 A 或 B，不要其他内容。
```

### 知识库问答

```
你是专业的招商顾问，基于知识库检索结果回答用户问题。

回答要求：
1. 优先使用知识库检索到的内容回答
2. 如果知识库内容不足，可以补充你的背景知识
3. 回答要条理清晰、重点突出
4. 标注信息来源

用户问题：{{#input_1efc6.user_input#}}

知识库检索结果：
{{#knowledge_retriever_834c6.retrieved_output#}}
```

### 结果判断

```
你是结果校验助手，判断知识库检索结果是否有效。

判断标准：
- 有有效内容（相关政策、园区、案例信息）输出：{"has_result": true}
- 无有效内容（空、无关、不相关）输出：{"has_result": false}

检索结果：{{#knowledge_retriever_834c6.retrieved_output#}}

严格按 JSON 格式输出，不要解释。
```

### 需求提取

```
你是招商助手，擅长理解企业投资咨询需求。请从用户输入中提取关键信息。

用户输入：{{#input_1efc6.user_input#}}

请按 JSON 格式输出：
{
  "咨询类型": "政策询问 | 园区询问 | 产业询问 | 投资评估 | 其他",
  "提及企业": "企业名称（如有）",
  "提及行业": "行业（如有）",
  "核心诉求": "用户最关心的问题（50 字内）",
  "检索关键词": ["关键词 1", "关键词 2", "关键词 3"]
}
```

### 检索 Query 生成

```
你是检索 Query 生成专家，根据用户需求生成精准检索 Query。

用户原始输入：{{#input_1efc6.user_input#}}
提取关键词：{{#llm_b9869.output#}}

请生成 1 个综合检索 Query（涵盖政策、园区、产业信息）。
格式：Query: {{关键词}} 深汕 政策 园区 配套

直接输出 Query，不要解释。
```

## 注意事项

### 必须遵守的规则

1. **唯一 ID 生成**: 每个节点必须有唯一的 ID，格式为 `类型_随机后缀`（如 `start_654ad`、`llm_ad8b7`）
2. **变量引用格式**: 必须使用 `{{#节点 ID.变量名#}}` 格式
3. **边连接完整**: 所有节点必须正确连接
4. **条件分支配置**: 条件节点的 sourceHandle 必须与条件 ID 对应
5. **JSON 格式**: 严格遵循 JSON 格式规范，注意转义字符
6. **知识库配置**: 只使用实际存在的知识库 ID 和名称，不要虚构
7. **联网检索输入**: Tool 节点的 query 必须使用 `{{#input_xxx.user_input#}}` 引用用户原始输入
8. **输出节点引用**: output 节点的 message 必须引用最终的 LLM 节点输出
9. **多分支输出处理**: 当多个分支汇聚到一个节点时，必须在提示词中明确引用所有可能的上游输出变量，不能使用未定义的变量
10. **知识库 ID 确认**: `knowledge_select_multi` 中的 `key` 字段是知识库的 ID（整数），必须向用户确认或使用占位值并提示用户修改

### 常见错误避免

1. **变量引用错误**
   - ❌ 错误：`{{节点 ID.变量}}` 或 `{节点 ID.变量}`
   - ✅ 正确：`{{#节点 ID.变量#}}`

2. **缺少节点连接**
   - ❌ 错误：节点孤立未连接
   - ✅ 正确：确保所有节点都在 edges 中有连接关系

3. **条件分支 ID 不匹配**
   - ❌ 错误：sourceHandle 与条件 ID 不一致
   - ✅ 正确：sourceHandle 必须等于 condition.value[0].id

4. **节点 ID 重复**
   - ❌ 错误：多个节点使用相同 ID
   - ✅ 正确：每个节点使用唯一 ID

5. **Position 重叠**
   - ❌ 错误：多个节点坐标相同或间距过小
   - ✅ 正确：合理规划节点位置，使用 834px 列间距，分支间≥600px

6. **联网检索配置错误**
   - ❌ 错误：`query: "{{#start_xxx.user_info#}} 搜索词"`
   - ✅ 正确：`query: "{{#input_xxx.user_input#}} 搜索词"`

7. **输出节点引用错误**
   - ❌ 错误：引用中间节点而非最终整合节点
   - ✅ 正确：引用最终的 LLM 节点输出

8. **使用不存在的知识库**
   - ❌ 错误：使用未配置或虚构的知识库 ID
   - ✅ 正确：只使用用户提供的、实际存在的知识库

9. **多分支输出变量引用**
   - ❌ 错误：使用未定义的变量，如 `{{#merged_output#}}`
   - ✅ 正确：明确引用所有可能的上游节点输出，如：
     ```
     海洋知识库回答：{{#llm_ocean_knowledge_answer.output#}}
     海洋联网回答：{{#llm_ocean_web_answer.output#}}
     招商知识库回答：{{#llm_invest_knowledge_answer.output#}}
     招商联网回答：{{#llm_invest_web_answer.output#}}
     普通对话回答：{{#llm_chat_response.output#}}
     请使用非空的那个回答作为最终输出。
     ```

10. **联网检索变量混淆**
    - ❌ 错误：`query: "{{#start_xxx.user_info#}} 搜索词"`（user_info 是空变量）
    - ✅ 正确：`query: "{{#input_xxx.user_input#}} 搜索词"` 或 `query: "固定搜索关键词"`

9. **多分支输出变量引用**
   - ❌ 错误：使用未定义的变量，如 `{{#merged_output#}}`
   - ✅ 正确：明确引用所有可能的上游节点输出，如：
     ```
     海洋知识库回答：{{#llm_ocean_knowledge_answer.output#}}
     海洋联网回答：{{#llm_ocean_web_answer.output#}}
     招商知识库回答：{{#llm_invest_knowledge_answer.output#}}
     招商联网回答：{{#llm_invest_web_answer.output#}}
     普通对话回答：{{#llm_chat_response.output#}}
     请使用非空的那个回答作为最终输出。
     ```

10. **联网检索变量混淆**
    - ❌ 错误：`query: "{{#start_xxx.user_info#}} 搜索词"`（user_info 是空变量）
    - ✅ 正确：`query: "{{#input_xxx.user_input#}} 搜索词"` 或 `query: "固定搜索关键词"`

### 布局最佳实践

1. **使用动态高度计算**: 根据节点实际高度（measured.height）计算垂直布局
2. **保持分支对齐**: 同一分支的节点 Y 坐标一致
3. **避免视觉拥挤**: 分支间垂直距离≥600px
4. **中心对齐主干**: 主干流程节点保持中心线对齐
5. **viewport 配置**: zoom: 0.5-0.6, x: 400, y: 300

## 输出格式

生成的 JSON 文件必须是完整的、可直接导入毕昇平台的格式：

```json
{
  "status": 2,
  "user_id": 1,
  "description": "工作流描述",
  "name": "工作流名称",
  "flow_type": 10,
  "id": "唯一 ID（32 位）",
  "nodes": [
    // Start 节点
    // Input 节点
    // 其他处理节点
    // Output 节点
  ],
  "edges": [
    // 节点连接关系
  ],
  "viewport": {"x": 400, "y": 300, "zoom": 0.5}
}
```

## 质量标准

### 合格标准（必达）

- JSON 格式正确，可以被解析
- 包含完整的 nodes、edges 配置
- 至少包含 start、input、output 节点
- 节点间有正确的连接关系
- 变量引用格式正确
- 所有必填字段完整
- 布局合理，节点不重叠

### 优秀标准（建议）

- 提示词设计专业，符合业务需求
- 节点布局美观，逻辑清晰
- 包含适当的条件分支处理
- 支持知识库检索功能
- 包含开场引导和预设问题
- 变量命名语义化
- viewport 配置合理

## 触发关键词

自动触发 bisheng-workflow-generator skill 的关键词：

- "生成毕昇工作流"
- "创建毕昇工作流"
- "毕昇工作流"
- "bisheng workflow"
- "毕升工作流"

## 更新日志

### v2.1.0 (2026-02-28)

- **新增**：多分支输出变量引用规则（基于实际修复案例）
- **新增**：知识库 ID 配置详细说明（`knowledge_select_multi` 的 `key` 是整数 ID）
- **新增**：常见错误避免第 9-10 条（多分支输出引用、联网检索变量混淆）
- **更新**：必须遵守的规则新增第 9-10 条
- **更新**：知识库检索节点配置说明，添加完整示例
- **修复**：更新日志版本号和日期

### v2.0.0 (2026-02-28)

- 新增节点动态高度计算规则
- 优化布局算法，避免节点重叠
- 修复联网检索节点 query 配置问题
- 修复输出节点引用问题
- 添加知识库验证规则
- 完善布局验证清单

### v1.0.0 (2026-02-27)

- 初始版本
- 支持所有主要节点类型
- 完整的工作流生成能力
- 智能节点连接
- 规范格式输出

## 技术支持

参考资源：

- 毕昇 GitHub: https://github.com/dataelement/bisheng
- 毕昇官网：https://www.bisheng.ai
- 毕昇文档：https://docs.bisheng.ai
