# 毕昇工作流 JSON 结构详解

本文档详细说明毕昇 (BiSheng) 工作流 JSON 文件的完整结构和字段含义。

## 文件结构概览

```json
{
  "status": 2,                    // 状态：2=已发布
  "user_id": 1,                   // 用户 ID
  "description": "工作流描述",     // 工作流描述
  "guide_word": null,             // 开场白
  "update_time": "2026-01-01T00:00:00",  // 更新时间
  "name": "工作流名称",           // 工作流名称
  "logo": "",                     // Logo URL
  "flow_type": 10,                // 工作流类型：10=标准工作流
  "create_time": "2026-01-01T00:00:00",  // 创建时间
  "id": "32 位唯一 ID",            // 工作流唯一 ID
  "nodes": [],                    // 节点列表
  "edges": [],                    // 边连接列表
  "viewport": {                   // 画布视图配置
    "x": 0,
    "y": 0,
    "zoom": 1
  }
}
```

## 顶层配置详解

### 必填字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `status` | int | 工作流状态 | `2` (已发布) |
| `flow_type` | int | 工作流类型 | `10` (标准工作流) |
| `name` | string | 工作流名称 | `"深汕招商智能体"` |
| `description` | string | 工作流描述 | `"聚焦深汕产业布局..."` |
| `id` | string | 32 位唯一 ID | `"9c8889e922374e368c34a139496095b1"` |

### 可选字段

| 字段 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `guide_word` | string/null | 开场白 | `null` |
| `logo` | string | Logo URL | `""` |
| `user_id` | int | 用户 ID | `1` |
| `create_time` | string | 创建时间 | ISO8601 |
| `update_time` | string | 更新时间 | ISO8601 |

## Graph 图结构

### Nodes (节点)

每个节点的通用结构：

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
  "position": {
    "x": 100,
    "y": 200
  },
  "measured": {
    "width": 334,
    "height": 500
  }
}
```

### Edges (边连接)

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

## 节点类型详细配置

### Start 开始节点

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
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 80, "y": 282},
  "measured": {"width": 334, "height": 600}
}
```

**输出变量：**
- `user_info`: 用户信息
- `current_time`: 当前时间
- `chat_history`: 聊天历史
- `preset_question`: 预设问题

### Input 输入节点

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
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 450, "y": 282},
  "measured": {"width": 334, "height": 500}
}
```

**输出变量：**
- `user_input`: 用户输入的文本
- `dialog_files_content`: 上传文件的内容

### LLM 大语言模型节点

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
            "required": true,
            "varZh": {
              "input_1efc6.user_input": "输入/user_input"
            }
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
  "position": {"x": 800, "y": 282},
  "measured": {"width": 334, "height": 700}
}
```

**输出变量：**
- `output`: LLM 生成的输出文本

### Knowledge Retriever 知识库检索节点

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
            "varZh": {
              "llm_afcdd.output": "上游节点/output"
            },
            "required": true
          },
          {
            "key": "knowledge",
            "type": "knowledge_select_multi",
            "label": "知识库",
            "value": {
              "type": "knowledge",
              "value": [
                {"key": 6, "label": "招商引资相关政策"}
              ]
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
            "value": [
              {"key": "retrieved_output", "label": "检索结果"}
            ]
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

**检索配置参数：**

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `keyword_weight` | float | 关键词检索权重 | 0.4 |
| `vector_weight` | float | 向量检索权重 | 0.6 |
| `rerank_flag` | bool | 是否启用重排序 | false |
| `max_chunk_size` | int | 最大分块大小 | 15000 |

**输出变量：**
- `retrieved_output`: 检索到的文档内容

### Condition 条件判断节点

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
  "position": {"x": 1600, "y": 282},
  "measured": {"width": 562, "height": 348}
}
```

**比较运算符：**

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

**逻辑运算符：**
- `and`: 所有条件都满足
- `or`: 任一条件满足

### Tool 工具节点

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
  "position": {"x": 2000, "y": 282},
  "measured": {"width": 334, "height": 430}
}
```

**常用工具 key：**
- `web_search`: 联网搜索
- `http_request`: HTTP 请求

### Output 输出节点

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
              "msg": "{{#llm_1daec.output#}}",
              "files": []
            },
            "varZh": {
              "llm_1daec.output": "LLM 节点/output"
            },
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
  "position": {"x": 2400, "y": 282},
  "measured": {"width": 334, "height": 465}
}
```

### Code 代码执行节点

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

**代码要求：**
- 入口函数必须为 `main`
- 返回值必须是 `dict` 类型
- 输出变量需要在 `code_output` 中定义

## 变量引用规范

### 基本格式

```
{{#节点 ID.变量名#}}
```

### 示例

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

**varZh 字段：** 用于显示变量来源的中文说明（可选）

## 坐标系统

### 推荐布局

**核心原则：** 节点宽度固定（334px），高度动态变化，必须根据实际高度计算布局！

**水平布局（关键）：**
- 列间距 = 节点宽度 (334) + 安全间距 (500) = **834px**
- 起始 X: **-200**（给左侧留空间）
- 每列递增：834px

**垂直布局（关键）：**
- 最小垂直间距：**100px**（节点下边缘到下一节点上边缘）
- 推荐垂直间距：**150-200px**（美观布局）
- 分支间垂直距离：**≥600px**（避免视觉拥挤）

**水平流程：**
```
Start(-200, 0) → Input(634, 382) → LLM(1468, 109) → Output(2302, 300)
```

**垂直分支：**
```
                    → 分支 1(1250, -800)
Condition(2302, 500) →
                    → 分支 2(1250, 200)
```

**复杂分支布局（推荐）：**
```
主流程：Start → Input → 意图识别 → 条件分支

条件分支后：
                    海洋政策分支 (Y: -800)
                   /
条件节点 (Y: 500) —————— 招商引资分支 (Y: 200)
                   \
                    普通对话分支 (Y: 1200)

布局规则：
- 同一分支的所有节点保持 Y 坐标一致
- 相邻列节点 X 间距：834px
- 分支间 Y 间距：≥600px（考虑节点高度后不重叠）
```

## 最佳实践

### 1. ID 生成规则

使用时间戳确保唯一性：
```javascript
const id = Date.now().toString() + randomSuffix;
// 例："llm_ad8b7", "start_654ad"
```

### 2. 节点命名

- 使用中文描述性名称
- 避免过长（建议 10 字以内）
- 清晰表达节点功能

### 3. 提示词设计

- 系统提示词：定义角色和规则
- 用户提示词：包含输入变量
- 使用明确的输出格式要求

### 4. 错误处理

- 使用 Condition 节点验证输出
- Code 节点包含异常处理
- 提供默认值或错误提示

### 5. 性能优化

- 合理设置 temperature 和 max_tokens
- 避免不必要的节点
- 知识库检索设置合适的 top_k

### 6. 布局优化（重要）

**节点尺寸规格：**

| 节点类型 | 宽度 (px) | 高度范围 (px) |
|---------|----------|------------|
| start | 334 | 600-1100 |
| input | 334 | 268-500 |
| llm | 334 | 700-850 |
| knowledge_retriever | 334 | 135-600 |
| condition | 322 | 232-400 |
| tool | 334 | 410-500 |
| output | 334 | 433-500 |

**布局验证清单：**
- [ ] 所有节点 X 坐标间隔 ≥ 500px（边缘到边缘）
- [ ] 同一列不同分支的节点 Y 坐标间隔 ≥ 100px（考虑高度后）
- [ ] 同一分支的节点 Y 坐标对齐
- [ ] Condition 节点的分支 sourceHandle 与条件 ID 对应
- [ ] 所有节点最终连接到 output 节点
- [ ] viewport 配置合适（zoom: 0.5-0.6, x: 400, y: 300）

**常见布局错误：**
- ❌ 节点间距过小导致视觉拥挤
- ❌ 分支间垂直距离不足导致重叠
- ❌ 未考虑节点实际高度导致布局混乱
- ✅ 使用 834px 列间距，分支间≥600px

## 版本兼容性

| 毕昇版本 | JSON 版本 | 兼容性 |
|----------|----------|--------|
| v2.3.0+ | v3 | ✅ 完全支持 |
| v2.0.0-v2.2.x | v2 | ⚠️ 部分兼容 |
| < v2.0.0 | v1 | ❌ 不兼容 |

## 参考资料

- 毕昇 GitHub: https://github.com/dataelement/bisheng
- 毕昇官网：https://www.bisheng.ai
- 毕昇文档：https://docs.bisheng.ai
