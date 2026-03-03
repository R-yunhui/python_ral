---
name: bisheng-workflow-generator
description: 专业的毕昇 (BiSheng) 工作流 JSON 文件生成器，根据用户业务需求自动生成完整的毕昇工作流配置文件。当用户提到毕昇、bisheng、毕升工作流时自动触发。
---

# 毕昇 (BiSheng) 工作流生成器

专业的毕昇工作流 JSON 文件自动生成工具。

## 核心功能

- **完整工作流生成**: 自动生成包含 nodes、edges 的完整 JSON 文件
- **多节点支持**: 支持 start、input、output、llm、condition、knowledge_retriever、tool 等节点类型
- **智能连接**: 自动生成节点间的 edges 连接关系
- **参数配置**: 智能推荐模型参数、提示词配置
- **规范格式**: 严格遵循毕昇工作流 JSON 规范
- **动态布局**: 根据节点高度动态计算布局，避免重叠

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
  "name": "工作流名称",
  "flow_type": 10,
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

**作用**：接收用户输入。

**核心字段**：
- `tab`：必须包含 2 个 options（`dialog_input` 和 `form_input`）
- `user_input`：用户输入文本

**完整示例**：
```json
{
  "id": "input_1efc6",
  "data": {
    "v": "3",
    "id": "input_1efc6",
    "name": "输入",
    "type": "input",
    "description": "接收用户在会话页面的输入。",
    "tab": {
      "value": "dialog_input",
      "options": [
        {"key": "dialog_input", "help": "true", "label": "true"},
        {"key": "form_input", "help": "true", "label": "true"}
      ]
    },
    "group_params": [
      {
        "name": "接收文本",
        "params": [
          {"key": "user_input", "tab": "dialog_input", "type": "var", "label": "true", "global": "key"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 634, "y": 382},
  "measured": {"width": 334, "height": 268}
}
```

---

### 3. LLM 节点（常用）

**作用**：调用大模型处理任务。

**核心字段**：
- `tab`：必需，包含 `single` 和 `batch` 两个 options
- `model_id`：模型 ID（必需）
- `user_prompt`：用户提示词（必需，使用 `{{#节点 ID.变量名#}}` 引用变量）
- `output`：输出变量（必需包含 `global` 映射）
- `batch_variable`：必需，即使在 single 模式下也要包含

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
        {"key": "single", "help": "true", "label": "true"},
        {"key": "batch", "help": "true", "label": "true"}
      ]
    },
    "group_params": [
      {
        "name": "模型设置",
        "params": [
          {"key": "model_id", "type": "bisheng_model", "label": "true", "value": 5, "required": true, "placeholder": "true"}
        ]
      },
      {
        "name": "提示词",
        "params": [
          {"key": "system_prompt", "test": "var", "type": "var_textarea", "label": "true", "value": "你是专业的 AI 助手"},
          {"key": "user_prompt", "test": "var", "type": "var_textarea", "label": "true", "value": "用户问题：{{#input_1efc6.user_input#}}", "required": true}
        ]
      },
      {
        "name": "输出",
        "params": [
          {"key": "output_user", "help": "true", "type": "switch", "label": "true", "value": true},
          {"key": "output", "help": "true", "type": "var", "label": "true", "value": [], "global": "code:value.map(el => ({ label: el.label, value: el.key }))"},
          {"key": "batch_variable", "tab": "batch", "help": "true", "test": "var", "type": "user_question", "label": "true", "value": [], "global": "self", "linkage": "output", "required": true, "placeholder": "true"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 1468, "y": 109},
  "measured": {"width": 334, "height": 700}
}
```

**变量引用格式**：`{{#节点 ID.变量名#}}`

---

### 4. Knowledge Retriever 知识库检索节点（常用）

**作用**：从指定知识库中检索相关内容。

**核心字段**：
- `user_question`：检索问题（必需，引用上游变量）
- `knowledge`：知识库选择（必需，嵌套结构）
- `retrieved_result`：输出字段（必需包含 global 映射）

**完整示例**：
```json
{
  "id": "knowledge_retriever_xxx",
  "data": {
    "v": "2",
    "id": "knowledge_retriever_xxx",
    "name": "知识库检索",
    "type": "knowledge_retriever",
    "description": "从知识库中检索相关内容。",
    "group_params": [
      {
        "name": "知识库检索设置",
        "params": [
          {
            "key": "user_question",
            "type": "user_question",
            "label": "true",
            "value": ["llm_xxx.output"],
            "required": true
          },
          {
            "key": "knowledge",
            "type": "knowledge_select_multi",
            "label": "true",
            "value": {
              "type": "knowledge",
              "value": [
                {"key": 6, "label": "知识库名称"}
              ]
            },
            "required": true
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
            "value": [
              {"key": "retrieved_output", "label": "检索结果"}
            ],
            "global": "code:value.map(el => ({ label: el.label, value: el.key }))"
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 1200, "y": 282},
  "measured": {"width": 334, "height": 600}
}
```

**注意事项**：
1. knowledge 字段必须使用嵌套结构（type + value）
2. user_question 必须引用上游节点的输出变量
3. 输出字段必须包含 global 映射函数

---

### 5. Tool 工具节点（可选）

**作用**：调用外部工具。

**重要**：只使用毕昇平台真实存在的工具！默认工具：`web_search`（联网搜索）

**完整示例**：
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
          {"key": "query", "test": "var", "type": "var_textarea", "label": "true", "value": "{{#input_1efc6.user_input#}}", "required": true, "placeholder": "true"}
        ]
      },
      {
        "name": "输出",
        "params": [
          {"key": "output", "type": "var", "label": "true", "global": "key"}
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 850, "y": 282},
  "measured": {"width": 334, "height": 430}
}
```

**警告**：不要编造不存在的工具（如 `weather_query`）

---

### 6. Output 输出节点（必需）

**作用**：向用户发送结果，是工作流的自然结束点。

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

**注意**：毕昇不需要专门的 End 节点，Output 节点即为结束点。

---

### 多分支输出处理（重要）

当工作流包含**条件分支和多个处理节点**时，Output 节点的 `message` 字段需要特殊处理：

#### 方案 A：引用主要分支的输出（简单场景）

选择最主要的分支输出作为 message 的值：

```json
{
  "key": "message",
  "type": "var_textarea_file",
  "label": "true",
  "value": {
    "msg": "{{#llm_main_branch.output#}}",  // 引用主要分支的输出
    "files": []
  },
  "varZh": {
    "llm_main_branch.output": "主要分支/output",
    "llm_other_branch.output": "其他分支/output"  // 也要列出其他可能的输出
  },
  "global": "key",
  "required": true,
  "placeholder": "true"
}
```

**适用场景**：各分支输出格式相似，可以互相替代。

#### 方案 B：使用 Code 节点合并输出（推荐）

在 Output 节点前添加 Code 节点，根据条件选择正确的输出源：

```json
// Code 节点示例
{
  "id": "code_merge_xxx",
  "data": {
    "type": "code",
    "name": "合并输出",
    "group_params": [
      {
        "params": [
          {
            "key": "code",
            "value": "def main(arg1: str, arg2: str, branch: str) -> str:\n    # 根据分支选择输出\n    if branch == 'travel':\n        return arg1\n    elif branch == 'document':\n        return arg2\n    else:\n        return arg1  # 默认"
          }
        ]
      }
    ]
  }
}
```

然后在 Output 节点引用 Code 节点的输出：
```json
"msg": "{{#code_merge_xxx.output#}}"
```

#### 方案 C：各分支独立 Output 节点（复杂场景）

每个分支末尾都添加一个 Output 节点，直接输出该分支的结果。

**适用场景**：各分支输出格式差异大，需要不同的处理逻辑。

---

### varZh 字段说明

`varZh` 字段用于说明所有可能引用的输出变量，**必须包含所有分支的输出**：

```json
"varZh": {
  "llm_travel.output": "旅游规划助手/output",
  "llm_document.output": "文档处理助手/output",
  "llm_general.output": "普通问答助手/output"
}
```

**作用**：帮助毕昇平台识别所有可能的变量引用，避免运行时错误。

---

### 7. Condition 条件判断节点（常用）

**作用**：根据条件表达式执行不同的分支逻辑。

**比较运算符**：
| 运算符 | 说明 |
|--------|------|
| equals | 等于 |
| not_equals | 不等于 |
| contains | 包含 |
| not_contains | 不包含 |
| is_empty | 为空 |
| is_not_empty | 不为空 |
| greater_than | 大于 |
| less_than | 小于 |

**完整示例**：
```json
{
  "id": "condition_xxx",
  "data": {
    "v": "1",
    "id": "condition_xxx",
    "name": "条件分支",
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
                "id": "condition_id_1",
                "operator": "or",
                "conditions": [
                  {
                    "id": "cond_1",
                    "left_var": "llm_xxx.output",
                    "left_label": "意图识别/output",
                    "right_value": "A",
                    "right_value_type": "input",
                    "comparison_operation": "equals"
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
  "position": {"x": 1600, "y": 282},
  "measured": {"width": 562, "height": 348}
}
```

**边连接规则**：
1. 每个条件分支对应一个 sourceHandle（使用条件 ID）
2. 默认分支使用 `right_handle`
3. 边的 ID 格式：`xy-edge__源节点 ID 条件 ID-目标节点 IDleft_handle`

---

### 多分支条件判断（重要）

当需要**3 个或更多分支**时（如意图识别场景），使用以下格式：

#### 完整示例（3 分支）

```json
{
  "id": "condition_d8e1b",
  "data": {
    "v": "1",
    "id": "condition_d8e1b",
    "name": "意图分支",
    "type": "condition",
    "description": "根据意图识别结果，分发到不同的处理流程。",
    "group_params": [
      {
        "params": [
          {
            "key": "condition",
            "type": "condition",
            "label": "true",
            "value": [
              {
                "id": "travel_branch",  // 分支 1：旅游规划
                "operator": "or",
                "conditions": [
                  {
                    "id": "cond_travel_1",
                    "left_var": "llm_intent.output",
                    "left_label": "意图识别/output",
                    "right_value": "TRAVEL_PLANNING",
                    "right_value_type": "input",
                    "comparison_operation": "contains"
                  }
                ]
              },
              {
                "id": "doc_branch",  // 分支 2：文档处理
                "operator": "or",
                "conditions": [
                  {
                    "id": "cond_doc_1",
                    "left_var": "llm_intent.output",
                    "left_label": "意图识别/output",
                    "right_value": "DOCUMENT_PROCESSING",
                    "right_value_type": "input",
                    "comparison_operation": "contains"
                  }
                ]
              },
              {
                "id": "default_branch",  // 分支 3：默认/其他
                "operator": "or",
                "conditions": []  // 空条件表示兜底，处理所有其他情况
              }
            ],
            "required": true
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 2302, "y": 500},
  "measured": {"width": 562, "height": 448}
}
```

#### 关键要点

1. **分支 ID 命名**：使用语义化的名称（如 `travel_branch`、`doc_branch`、`default_branch`）
2. **默认分支**：
   - `conditions` 为空数组 `[]`
   - 作为兜底，处理无法匹配前序条件的情况
   - **必须连接到处理节点**（不能悬空）
3. **边的连接**：
   - 每个分支 ID 对应一条出边
   - 边的 `sourceHandle` 必须与分支 ID 一致
   - 示例：
     ```json
     {
       "source": "condition_d8e1b",
       "sourceHandle": "travel_branch",  // 与分支 ID 一致
       "target": "llm_travel"
     }
     ```

#### 分支数量与边的关系

- **Condition 节点的出边数 = 条件分支数量**
- 3 个分支 → 3 条出边
- 4 个分支 → 4 条出边
- 每个分支必须连接到一个处理节点（LLM、Tool、Output 等）

#### 常见意图分类示例

```json
// 旅游助手场景
{
  "id": "travel_branch",
  "conditions": [{"right_value": "TRAVEL_PLANNING", ...}]
},
{
  "id": "document_branch",
  "conditions": [{"right_value": "DOCUMENT_PROCESSING", ...}]
},
{
  "id": "default_branch",
  "conditions": []  // 普通问答、闲聊等
}

// 客服场景
{
  "id": "sales_branch",
  "conditions": [{"right_value": "SALES_INQUIRY", ...}]
},
{
  "id": "support_branch",
  "conditions": [{"right_value": "TECHNICAL_SUPPORT", ...}]
},
{
  "id": "complaint_branch",
  "conditions": [{"right_value": "COMPLAINT", ...}]
},
{
  "id": "default_branch",
  "conditions": []
}
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

1. **每个节点至多一个入边**（start 节点除外）
2. **节点可以有多个出边**（condition 等分支节点）
3. **Output→Input 循环边**：默认必需（多轮对话），除非用户明确要求单次执行
4. **条件分支**：sourceHandle 使用条件 ID

### 边的数量计算（重要）

#### 线性流程（无分支）

- **多轮对话**：节点数 + 1（Output→Input 循环边）
- **单次执行**：节点数 - 1

**示例**：Start → Input → LLM → Output → Input（循环）
- 节点数：4
- 边数：4 + 1 = 5 条

#### 条件分支流程

**总边数 = 主干边数 + 各分支的边数**

**示例 1**：3 分支意图识别工作流
```
Start → Input → LLM_Intent → Condition
                                   ├─ Branch_A → LLM_A ─┐
                                   ├─ Branch_B → LLM_B ─┼→ Output → Input（循环）
                                   └─ Branch_C → LLM_C ─┘
```

边数计算：
- Start → Input：1 条
- Input → LLM_Intent：1 条
- LLM_Intent → Condition：1 条
- Condition → 3 个分支：3 条
- 3 个分支 → LLM：3 条
- 3 个 LLM → Output：3 条
- Output → Input（循环）：1 条
- **总计**：13 条边

**示例 2**：2 分支工作流
```
Start → Input → Condition
                        ├─ Travel → LLM_Travel ─┐
                        └─ Doc → LLM_Doc ───────┼→ Output → Input（循环）
```

边数计算：
- Start → Input：1 条
- Input → Condition：1 条
- Condition → 2 个分支：2 条
- 2 个分支 → LLM：2 条
- 2 个 LLM → Output：2 条
- Output → Input（循环）：1 条
- **总计**：9 条边

#### 关键规则

- **Condition 节点的出边数 = 条件分支数量**
- 每个分支的边数 = 该分支的节点数 - 1
- 多轮对话必须包含 Output→Input 的循环边（1 条）

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
6. **边连接完整**: 所有节点必须正确连接
7. **条件分支**: sourceHandle 必须与条件 ID 对应
8. **knowledge 字段**: 必须使用嵌套结构
9. **output 字段**: 必须包含 `global` 映射函数
10. **Tool 节点**: query 必须使用 `{{#input_xxx.user_input#}}`
11. **Output 节点**: message 必须引用最终的 LLM 输出

### 常见错误

- ❌ 缺少 `position` 或 `measured` → ✅ 每个节点必须包含
- ❌ `data.id` 与外层 `id` 不一致 → ✅ 必须一致
- ❌ 缺少 `data.description` → ✅ 每个节点必需
- ❌ `{{节点 ID.变量}}` → ✅ `{{#节点 ID.变量#}}`
- ❌ 编造 `weather_query` → ✅ 使用 `web_search`
- ❌ knowledge 字段缺少 type → ✅ `{"type": "knowledge", "value": [...]}`

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
- 节点间有正确的连接关系
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

---

## 触发关键词

自动触发 bisheng-workflow-generator skill 的关键词：

- "生成毕昇工作流"
- "创建毕昇工作流"
- "毕昇工作流"
- "bisheng workflow"
- "毕升工作流"

---

## 完整示例：多分支意图识别工作流

以下是一个**3 分支意图识别工作流**的完整示例，可直接参考使用：

### 场景说明

**工作流名称**：个人旅游助手  
**功能**：识别用户意图，分别处理旅游规划、文档处理、普通问答三种场景

### 流程图

```
Start → Input → LLM_Intent → Condition
                                 ├─ Travel → LLM_Travel ─┐
                                 ├─ Doc → LLM_Doc ───────┼→ Output → Input（循环）
                                 └─ Default → LLM_General ┘
```

### 节点列表

| 节点 ID | 类型 | 名称 | 位置 |
|--------|------|------|------|
| `start_a7b3c` | start | 开始 | (-200, 282) |
| `input_b9d4e` | input | 输入 | (634, 382) |
| `llm_intent_c5f2a` | llm | 意图识别 | (1468, 109) |
| `condition_d8e1b` | condition | 意图分支 | (2302, 500) |
| `llm_travel_e3a9f` | llm | 旅游规划助手 | (3136, 109) |
| `llm_doc_f7c2d` | llm | 文档处理助手 | (3136, 882) |
| `llm_general_h2i5j` | llm | 普通问答助手 | (3136, 1655) |
| `output_g4h8i` | output | 输出 | (3970, 500) |

### 关键配置

#### 1. 意图识别 LLM 节点

```json
{
  "id": "llm_intent_c5f2a",
  "data": {
    "type": "llm",
    "name": "意图识别",
    "group_params": [
      {
        "name": "提示词",
        "params": [
          {
            "key": "system_prompt",
            "value": "你是一个意图识别助手。请分析用户的输入，判断其意图类型。\n\n意图分类：\n1. TRAVEL_PLANNING - 旅游规划\n2. DOCUMENT_PROCESSING - 文档处理\n3. GENERAL_CHAT - 普通问答/闲聊\n\n请只返回格式：INTENT: [意图类型]"
          }
        ]
      }
    ]
  }
}
```

#### 2. 条件分支节点（3 分支）

```json
{
  "id": "condition_d8e1b",
  "data": {
    "type": "condition",
    "group_params": [
      {
        "params": [
          {
            "key": "condition",
            "value": [
              {
                "id": "travel_branch",
                "conditions": [
                  {
                    "left_var": "llm_intent_c5f2a.output",
                    "right_value": "TRAVEL_PLANNING",
                    "comparison_operation": "contains"
                  }
                ]
              },
              {
                "id": "doc_branch",
                "conditions": [
                  {
                    "left_var": "llm_intent_c5f2a.output",
                    "right_value": "DOCUMENT_PROCESSING",
                    "comparison_operation": "contains"
                  }
                ]
              },
              {
                "id": "default_branch",
                "conditions": []  // 兜底，处理 GENERAL_CHAT 等其他情况
              }
            ]
          }
        ]
      }
    ]
  }
}
```

#### 3. Output 节点（多分支引用）

```json
{
  "id": "output_g4h8i",
  "data": {
    "type": "output",
    "group_params": [
      {
        "params": [
          {
            "key": "message",
            "value": {
              "msg": "{{#llm_travel_e3a9f.output#}}",  // 引用主分支输出
              "files": []
            },
            "varZh": {
              "llm_travel_e3a9f.output": "旅游规划助手/output",
              "llm_doc_f7c2d.output": "文档处理助手/output",
              "llm_general_h2i5j.output": "普通问答助手/output"
            }
          }
        ]
      }
    ]
  }
}
```

### 边连接列表（共 13 条）

```json
"edges": [
  // 主干流程（4 条）
  {"source": "start_a7b3c", "target": "input_b9d4e"},
  {"source": "input_b9d4e", "target": "llm_intent_c5f2a"},
  {"source": "llm_intent_c5f2a", "target": "condition_d8e1b"},
  
  // 条件分支（3 条）
  {"source": "condition_d8e1b", "sourceHandle": "travel_branch", "target": "llm_travel_e3a9f"},
  {"source": "condition_d8e1b", "sourceHandle": "doc_branch", "target": "llm_doc_f7c2d"},
  {"source": "condition_d8e1b", "sourceHandle": "default_branch", "target": "llm_general_h2i5j"},
  
  // 分支到 Output（3 条）
  {"source": "llm_travel_e3a9f", "target": "output_g4h8i"},
  {"source": "llm_doc_f7c2d", "target": "output_g4h8i"},
  {"source": "llm_general_h2i5j", "target": "output_g4h8i"},
  
  // 循环边（1 条）
  {"source": "output_g4h8i", "target": "input_b9d4e"}
]
```

### 检查清单

✅ 所有节点包含 `position` 和 `measured`  
✅ `data.id` 与外层 `id` 一致  
✅ 每个节点有 `description`  
✅ 条件分支有 3 个分支，包含默认分支  
✅ 边的 `sourceHandle` 与分支 ID 一致  
✅ Output 节点 `varZh` 包含所有分支的输出  
✅ 包含 Output→Input 循环边（多轮对话）  
✅ 变量引用使用 `{{#节点 ID.变量#}}` 格式  

---

### 完整 JSON 文件

参考示例文件：`examples/personal-travel-assistant.json`

该示例包含：
- 完整的 8 个节点配置
- 13 条边连接
- 详细的提示词配置
- 正确的布局坐标
- 可直接导入毕昇平台使用
