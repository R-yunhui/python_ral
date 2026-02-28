# Start 节点字段完整说明

本文档详细说明毕昇工作流 Start 节点的完整字段配置。

## 完整结构

Start 节点包含两个主要分组：

### 1. 开场引导

```json
{
  "name": "开场引导",
  "params": [
    {
      "key": "guide_word",
      "type": "textarea",
      "label": "true",
      "value": "欢迎语内容",
      "placeholder": "true"
    },
    {
      "key": "guide_question",
      "type": "input_list",
      "label": "true",
      "value": ["问题 1", "问题 2", "问题 3"],
      "placeholder": "true"
    }
  ]
}
```

### 2. 全局变量（必须包含 5 个字段）

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
        {"key": "pq_002", "value": "预设问题 2"},
        {"key": "pq_003", "value": "预设问题 3"}
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

## 字段详细说明

### 基础系统字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `user_info` | var | "" | 用户信息（自动填充） |
| `current_time` | var | "" | 当前时间（自动填充） |
| `chat_history` | chat_history_num | 10 | 保留的聊天历史消息数量 |

### preset_question（预设问题）

**作用**: 在界面上显示预设问题按钮，用户可以快速点击提问。

**格式要求**:
```json
{
  "key": "preset_question",
  "help": "true",
  "type": "input_list",
  "label": "true",
  "value": [
    {"key": "唯一 ID1", "value": "预设问题文本 1"},
    {"key": "唯一 ID2", "value": "预设问题文本 2"},
    {"key": "唯一 ID3", "value": "预设问题文本 3"}
  ],
  "global": "item:input_list",
  "placeholder": "true"
}
```

**注意事项**:
- `value` 数组中的每个元素必须包含 `key` 和 `value`
- `key` 需要生成唯一 ID（建议使用 `pq_` 前缀 + 时间戳或随机数）
- 通常设置 3-5 个预设问题
- 最后一个元素的 `value` 可以为空字符串（作为占位符）

### custom_variables（自定义变量）

**作用**: 存储用户自定义的全局变量，用于工作流中的数据处理。

**格式要求**:
```json
{
  "key": "custom_variables",
  "help": "true",
  "type": "global_var",
  "label": "true",
  "value": [],
  "global": "item:input_list"
}
```

**注意事项**:
- `value` 通常为空数组 `[]`
- 可以根据需要在运行时动态添加变量
- `type` 必须为 `"global_var"`

## 常见错误

### ❌ 错误 1：缺少 preset_question 或 custom_variables

```json
{
  "name": "全局变量",
  "params": [
    {"key": "user_info", "type": "var", "label": "true", "value": "", "global": "key"},
    {"key": "current_time", "type": "var", "label": "true", "value": "", "global": "key"},
    {"key": "chat_history", "type": "chat_history_num", "value": 10, "global": "key"}
    // 缺少 preset_question 和 custom_variables
  ]
}
```

**结果**: 毕昇平台导入时可能报错 "Cannot read properties of undefined (reading 'map')"

### ❌ 错误 2：preset_question 格式错误

```json
{
  "key": "preset_question",
  "type": "input_list",
  "value": ["问题 1", "问题 2"]  // ❌ 错误：应该是对象数组
}
```

**正确格式**:
```json
{
  "key": "preset_question",
  "type": "input_list",
  "value": [
    {"key": "pq_001", "value": "问题 1"},
    {"key": "pq_002", "value": "问题 2"}
  ]
}
```

### ❌ 错误 3：缺少必需属性

```json
{
  "key": "preset_question",
  "type": "input_list",
  "value": [...]
  // 缺少 help, label, global, placeholder
}
```

**正确格式**: 必须包含 `help: "true"`, `label: "true"`, `global: "item:input_list"`, `placeholder: "true"`

## 完整示例

参考以下示例文件：

1. `examples/example-simple-qa.json` - 简单问答工作流
2. `examples/example-knowledge-retrieval.json` - 知识库检索工作流
3. `bisheng_workflow_json/shenshanzhaoshangzhinengti.json` - 真实生产工作流

## 检查清单

在导入工作流之前，请检查 Start 节点是否包含：

- [ ] `user_info` 字段
- [ ] `current_time` 字段
- [ ] `chat_history` 字段
- [ ] `preset_question` 字段（格式正确）
- [ ] `custom_variables` 字段
- [ ] 所有字段的 `label` 都是 `"true"`
- [ ] 所有字段的 `global` 属性正确

---

**重要提示**: 这 5 个字段是毕昇平台 Start 节点的标准配置，缺少任何一个都可能导致导入错误！
