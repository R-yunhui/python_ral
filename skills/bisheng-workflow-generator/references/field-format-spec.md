# 毕昇工作流 JSON 字段格式规范

本文档详细说明毕昇工作流 JSON 文件中各字段的正确格式，避免导入时出现错误。

## 常见错误：Cannot read properties of undefined (reading 'map')

这个错误通常是由于 JSON 字段格式不符合毕昇平台预期导致的。

## label 字段格式

### ❌ 错误格式

```json
{
  "key": "guide_word",
  "type": "textarea",
  "label": "开场白",
  "value": ""
}
```

**问题**: label 字段使用了中文描述，毕昇平台无法解析。

### ✅ 正确格式

```json
{
  "key": "guide_word",
  "type": "textarea",
  "label": "true",
  "value": "",
  "placeholder": "true"
}
```

**说明**: 
- `label` 字段应该是 `"true"` 或 `"false"`
- 添加 `placeholder` 属性（也是 `"true"` 或 `"false"`）

## 各类型字段的必需属性

### 文本/数字字段

```json
{
  "key": "system_prompt",
  "type": "var_textarea",
  "label": "true",
  "value": "提示词内容"
}
```

### 开关字段

```json
{
  "key": "output_user",
  "type": "switch",
  "label": "true",
  "value": true
}
```

### 列表字段

```json
{
  "key": "guide_question",
  "type": "input_list",
  "label": "true",
  "value": ["问题 1", "问题 2"],
  "placeholder": "true"
}
```

### 变量字段

```json
{
  "key": "user_input",
  "type": "var",
  "label": "true",
  "global": "key"
}
```

## output 字段格式

### ❌ 错误格式

```json
{
  "key": "output",
  "type": "var",
  "value": []
}
```

### ✅ 正确格式

```json
{
  "key": "output",
  "type": "var",
  "label": "true",
  "value": [],
  "global": "code:value.map(el => ({ label: el.label, value: el.key }))"
}
```

**说明**: output 字段必须包含 `global` 映射函数。

## knowledge 字段格式

### ❌ 错误格式

```json
{
  "key": "knowledge",
  "value": [
    {"key": 6, "label": "招商引资相关政策"}
  ]
}
```

### ✅ 正确格式

```json
{
  "key": "knowledge",
  "type": "knowledge_select_multi",
  "label": "true",
  "value": {
    "type": "knowledge",
    "value": [
      {"key": 6, "label": "招商引资相关政策"}
    ]
  },
  "required": true,
  "placeholder": "true"
}
```

**说明**: knowledge 字段需要嵌套结构，包含 `type` 和完整的属性。

## varZh 字段（变量中文说明）

varZh 字段用于映射变量的中文说明，帮助在界面上显示变量来源。

```json
{
  "key": "user_prompt",
  "type": "var_textarea",
  "label": "true",
  "value": "用户输入：{{#input_001.user_input#}}",
  "varZh": {
    "input_001.user_input": "输入/user_input",
    "knowledge_retriever_001.retrieved_output": "知识库检索/retrieved_output"
  },
  "required": true
}
```

## 完整示例：LLM 节点

```json
{
  "id": "llm_001",
  "data": {
    "v": "2",
    "id": "llm_001",
    "name": "AI 回答",
    "type": "llm",
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
          {
            "key": "model_id",
            "type": "bisheng_model",
            "label": "true",
            "value": 5,
            "required": true,
            "placeholder": "true"
          },
          {
            "key": "temperature",
            "step": 0.1,
            "type": "slide",
            "label": "true",
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
            "test": "var",
            "type": "var_textarea",
            "label": "true",
            "value": "你是一个 AI 助手"
          },
          {
            "key": "user_prompt",
            "test": "var",
            "type": "var_textarea",
            "label": "true",
            "value": "用户问题：{{#input_001.user_input#}}",
            "varZh": {
              "input_001.user_input": "输入/user_input"
            },
            "required": true
          }
        ]
      },
      {
        "name": "输出",
        "params": [
          {
            "key": "output_user",
            "help": "true",
            "type": "switch",
            "label": "true",
            "value": true
          },
          {
            "key": "output",
            "help": "true",
            "type": "var",
            "label": "true",
            "value": [],
            "global": "code:value.map(el => ({ label: el.label, value: el.key }))"
          }
        ]
      }
    ]
  },
  "type": "flowNode",
  "position": {"x": 850, "y": 282}
}
```

## 检查清单

在导入工作流之前，请检查：

- [ ] 所有 `label` 字段都是 `"true"` 或 `"false"`
- [ ] 所有 `output` 字段都包含 `global` 映射函数
- [ ] `knowledge` 字段使用嵌套结构
- [ ] 变量引用使用 `{{#节点 ID.变量名#}}` 格式
- [ ] 添加了必要的 `varZh` 映射
- [ ] JSON 格式正确（可以使用 JSON 验证工具）

## 参考资料

- 示例文件：`examples/example-simple-qa.json`
- 示例文件：`examples/example-knowledge-retrieval.json`
- 真实工作流：`bisheng_workflow_json/shenshanzhaoshangzhinengti.json`

## Start 节点的必需字段（重要）

Start 节点的 `全局变量` 分组必须包含以下 5 个字段：

```json
{
  "name": "全局变量",
  "params": [
    {"key": "user_info", "type": "var", "label": "true", "value": "", "global": "key"},
    {"key": "current_time", "type": "var", "label": "true", "value": "", "global": "key"},
    {"key": "chat_history", "type": "chat_history_num", "value": 10, "global": "key"},
    {
      "key": "preset_question",
      "help": "true",
      "type": "input_list",
      "label": "true",
      "value": [
        {"key": "pq_001", "value": "预设问题 1"},
        {"key": "pq_002", "value": "预设问题 2"}
      ],
      "global": "item:input_list",
      "placeholder": "true"
    },
    {
      "key": "custom_variables",
      "help": "true",
      "type": "global_var",
      "label": "true",
      "value": [],
      "global": "item:input_list"
    }
  ]
}
```

**字段说明:**

| 字段 | 类型 | 说明 | 是否必需 |
|------|------|------|----------|
| `user_info` | var | 用户信息 | ✅ 必需 |
| `current_time` | var | 当前时间 | ✅ 必需 |
| `chat_history` | chat_history_num | 聊天历史数量 | ✅ 必需 |
| `preset_question` | input_list | 预设问题列表 | ✅ 必需 |
| `custom_variables` | global_var | 自定义全局变量 | ✅ 必需 |

**preset_question 格式:**
- `type`: `"input_list"`
- `value`: 数组，每个元素包含 `key` 和 `value`
- `key`: 需要生成唯一 ID（如 `pq_001`, `pq_002`）
- `global`: `"item:input_list"`

**custom_variables 格式:**
- `type`: `"global_var"`
- `value`: 空数组 `[]`
- `global`: `"item:input_list"`

**注意**: 缺少这 5 个字段中的任何一个都可能导致毕昇平台导入错误！
