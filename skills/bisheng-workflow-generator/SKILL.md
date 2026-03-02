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
    "group_params": []
  },
  "type": "flowNode",
  "position": {"x": 100, "y": 200},
  "measured": {"width": 334, "height": 500}
}
```

**ID 命名规范:** `类型_随机后缀`（如 `start_654ad`、`llm_ad8b7`）

### 核心节点说明

#### 1. Start 开始节点（必需）

**作用**：工作流起始点，包含开场引导和全局变量。

**必需字段**：
- `guide_word`：开场白
- `guide_question`：引导问题列表
- **全局变量 5 个**：`user_info`、`current_time`、`chat_history`、`preset_question`、`custom_variables`

**示例**：
```json
{
  "id": "start_654ad",
  "data": {
    "v": "3",
    "name": "开始",
    "type": "start",
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
  }
}
```

#### 2. Input 输入节点（必需）

**作用**：接收用户输入。

**核心字段**：
- `user_input`：用户输入文本（必需）
- `tab`：支持 `dialog_input` 和 `form_input` 两种模式（**必须包含 2 个 options**）

**示例**：
```json
{
  "id": "input_1efc6",
  "data": {
    "v": "3",
    "name": "输入",
    "type": "input",
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
  }
}
```

#### 3. LLM 节点（常用）

**作用**：调用大模型处理任务。

**核心字段**：
- `tab`：**必需**，包含 `single` 和 `batch` 两个 options
- `model_id`：模型 ID（必需）
- `system_prompt`：系统提示词
- `user_prompt`：用户提示词（必需，使用 `{{#节点 ID.变量名#}}` 引用变量）
- `output`：输出变量（必需包含 `global` 映射）
- `batch_variable`：**必需**，即使在 single 模式下也要包含

**示例**：
```json
{
  "id": "llm_ad8b7",
  "data": {
    "v": "2",
    "tab": {
      "value": "single",
      "options": [
        {"key": "single", "help": "true", "label": "true"},
        {"key": "batch", "help": "true", "label": "true"}
      ]
    },
    "name": "LLM 节点",
    "type": "llm",
    "group_params": [
      {
        "params": [
          {
            "key": "batch_variable",
            "tab": "batch",
            "help": "true",
            "test": "var",
            "type": "user_question",
            "label": "true",
            "value": [],
            "global": "self",
            "linkage": "output",
            "required": true,
            "placeholder": "true"
          }
        ]
      },
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
          {"key": "user_prompt", "test": "var", "type": "var_textarea", "label": "true", "value": "用户输入：{{#input_1efc6.user_input#}}", "required": true}
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
  }
}
```

**变量引用格式**：`{{#节点 ID.变量名#}}`

#### 4. Tool 工具节点（可选）

**作用**：调用外部工具。

**重要**：只使用毕昇平台真实存在的工具！

**默认工具**：`web_search`（联网搜索）

**示例**：
```json
{
  "id": "tool_982ee",
  "data": {
    "name": "联网搜索",
    "type": "tool",
    "tool_key": "web_search",
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
  }
}
```

**警告**：不要编造不存在的工具（如 `weather_query`）

#### 5. Output 输出节点（必需）

**作用**：向用户发送结果，是工作流的自然结束点。

**核心字段**：
- `message`：输出内容（必需，包含 `msg` 和 `files`）
- `output_result`：输出表单（必需，**必须包含 `options: []`**）

**示例**：
```json
{
  "id": "output_5b20b",
  "data": {
    "v": "2",
    "name": "输出",
    "type": "output",
    "group_params": [
      {
        "params": [
          {"key": "message", "type": "var_textarea_file", "label": "true", "value": {"msg": "{{#llm_ad8b7.output#}}", "files": []}, "global": "key", "required": true, "placeholder": "true"},
          {"key": "output_result", "type": "output_form", "label": "true", "value": {"type": "", "value": ""}, "global": "value.type=input", "options": [], "required": false}
        ]
      }
    ]
  }
}
```

**注意**：毕昇不需要专门的 End 节点，Output 节点即为结束点。

### 其他节点

- **Condition**：条件判断节点（用于分支逻辑）
- **Knowledge Retriever**：知识库检索节点
- **Code**：代码执行节点（执行 Python 代码）
- **RAG**：RAG 检索节点

**详细说明请参考 examples 目录中的完整示例文件。**

## Edges 边连接

边定义节点之间的连接关系。

### 基本结构

```json
{
  "id": "xy-edge__源节点 IDright_handle-目标节点 IDleft_handle",
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
3. **Output 节点是工作流的自然结束点**
   - 添加 Output→Input 循环边 = 多轮对话（默认）
   - 不添加循环边 = 单次执行
4. **条件分支**：sourceHandle 使用条件 ID
5. **边的数量**：
   - **默认（多轮对话）**：5 条边（Start→Input→Process→Output→Input 循环）
   - **特殊（单次执行）**：4 条边（仅当用户明确要求）
6. **输出即可用**：生成的 JSON 必须可直接导入毕昇平台

### 循环边（默认必需）

**规则**：除非用户明确要求单次执行，否则**必须包含**Output→Input 循环边。

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

### 线性布局示例

```
Start(-200, 0) → Input(634, 382) → LLM(1468, 109) → Output(2302, 300)
```

### 验证清单

- [ ] 节点 X 坐标间隔 ≥ 500px
- [ ] 分支间 Y 间距 ≥ 600px
- [ ] viewport 配置：zoom: 0.5-0.6, x: 400, y: 300

## 实际案例

完整的工作流案例请参考 `examples/` 目录：

- `example-simple-qa.json` - 简单问答工作流
- `example-knowledge-retrieval.json` - 知识库检索工作流

**提示词设计原则**：
1. 系统提示词：定义角色和规则
2. 用户提示词：包含输入变量（使用 `{{#节点 ID.变量名#}}`）
3. 明确的输出格式要求

## 注意事项

### 必须遵守的规则

1. **唯一 ID 生成**: `类型_随机后缀`（如 `start_654ad`）
2. **变量引用格式**: `{{#节点 ID.变量名#}}`
3. **边连接完整**: 所有节点必须正确连接
4. **条件分支**: sourceHandle 必须与条件 ID 对应
5. **JSON 格式**: 严格遵循 JSON 规范
6. **知识库配置**: 只使用实际存在的 ID 和名称
7. **Tool 节点**: query 必须使用 `{{#input_xxx.user_input#}}`
8. **Output 节点**: message 必须引用最终的 LLM 输出
9. **多分支输出**: 必须明确引用所有可能的上游输出变量
10. **工具使用**: 只使用 `web_search`，不要编造工具

### 常见错误

- ❌ `{{节点 ID.变量}}` → ✅ `{{#节点 ID.变量#}}`
- ❌ 编造 `weather_query` → ✅ 使用 `web_search`
- ❌ `query: "{{#start_xxx.user_info#}}" `→ ✅ `query: "{{#input_xxx.user_input#}}"`
- ❌ 引用中间节点 → ✅ 引用最终 LLM 节点
- ❌ 节点坐标重叠 → ✅ 使用 834px 列间距，分支间≥600px

## 输出格式

生成的 JSON 文件必须是完整的、可直接导入毕昇平台的格式：

**重要原则**：
1. **输出即可用**：生成的 JSON 必须可以直接导入毕昇平台并正常工作
2. **默认多轮对话**：除非用户明确要求单次执行，否则必须包含 Output→Input 循环边
3. **字段完整**：所有必需字段（custom_variables、output_result 等）必须包含

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
    {
      "id": "xy-edge__start_654adright_handle-input_1efc6left_handle",
      "type": "customEdge",
      "source": "start_654ad",
      "target": "input_1efc6",
      "sourceHandle": "right_handle",
      "targetHandle": "left_handle",
      "animated": true
    },
    {
      "id": "xy-edge__input_1efc6right_handle-tool_982eeleft_handle",
      "type": "customEdge",
      "source": "input_1efc6",
      "target": "tool_982ee",
      "sourceHandle": "right_handle",
      "targetHandle": "left_handle",
      "animated": true
    },
    {
      "id": "xy-edge__tool_982eeright_handle-llm_ad8b7left_handle",
      "type": "customEdge",
      "source": "tool_982ee",
      "target": "llm_ad8b7",
      "sourceHandle": "right_handle",
      "targetHandle": "left_handle",
      "animated": true
    },
    {
      "id": "xy-edge__llm_ad8b7right_handle-output_5b20bleft_handle",
      "type": "customEdge",
      "source": "llm_ad8b7",
      "target": "output_5b20b",
      "sourceHandle": "right_handle",
      "targetHandle": "left_handle",
      "animated": true
    },
    {
      "id": "xy-edge__output_5b20bright_handle-input_1efc6left_handle",
      "type": "customEdge",
      "source": "output_5b20b",
      "target": "input_1efc6",
      "sourceHandle": "right_handle",
      "targetHandle": "left_handle",
      "animated": true
    }
    // 默认生成 5 条边（多轮对话工作流）
    // 第 5 条边（Output→Input 循环）是默认必需的，支持多轮对话
    // 仅当用户明确要求单次执行时，才生成 4 条边（不包含循环边）
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
