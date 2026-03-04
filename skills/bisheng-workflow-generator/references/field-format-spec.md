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

## 各节点必填字段校验清单

### Start 节点
**必需字段**：
- [ ] `guide_word` (type: textarea, label: "true", placeholder: "true")
- [ ] `guide_question` (type: input_list, label: "true", placeholder: "true")
- [ ] `user_info` (type: var, label: "true", global: "key")
- [ ] `current_time` (type: var, label: "true", global: "key")
- [ ] `chat_history` (type: chat_history_num, value: 10, global: "key")
- [ ] `preset_question` (type: input_list, label: "true", global: "item:input_list", placeholder: "true")
  - value 格式：`[{"key": "pq_001", "value": "问题 1"}]`
- [ ] `custom_variables` (type: global_var, label: "true", global: "item:input_list")

**常见错误**：
❌ 缺少 5 个全局变量中的任何一个
❌ preset_question 的 value 不是数组格式
❌ custom_variables 的 type 错误

---

### Input 节点
**必需字段**：
- [ ] `tab` (必须包含 2 个 options: dialog_input 和 form_input，options 里含 `help: "true"`)
- [ ] `description` 必须为 `"接收用户在会话页面的输入，支持 2 种形式：对话框输入，表单输入。"`
- [ ] `user_input` (tab: dialog_input, type: var, label: "true", global: "key")
- [ ] 文件上传分组 (groupKey: "inputfile"，含 user_input_file、file_parse_mode、dialog_files_content 等 7 个字段)
- [ ] 推荐问题分组 (groupKey: "custom"，含 recommended_questions_flag、recommended_llm、recommended_system_prompt、recommended_history_num)
- [ ] 表单输入分组 (含 form_input，tab: form_input，global: "item:form_input")

**常见错误**：
❌ group_params 只有 `接收文本` 一个分组
❌ 缺少文件上传分组（user_input_file 等字段）
❌ 缺少推荐问题分组（recommended_llm 等字段）
❌ 缺少表单输入分组（form_input 字段）
❌ description 写成简化版 `"接收用户在会话页面的输入。"`
❌ measured.height 设为 268（正确值为 657）

---

### LLM 节点
**必需字段**：
- [ ] `tab` (options 只含 `key` 和 `label`，**不含 `help`**)
- [ ] `batch_variable` (在**第一个无名分组**中，不在输出分组)
- [ ] `model_id` (type: bisheng_model, label: "true", required: true)
- [ ] `user_prompt` (type: var_textarea, label: "true", required: true，含 varZh)
- [ ] `image_prompt` (在提示词分组中，type: image_prompt, value: [])
- [ ] `output` (type: var, label: "true", 必须包含 global 映射函数)

**group_params 正确顺序**：
1. 无名分组：`batch_variable`
2. 模型设置：`model_id`, `temperature`
3. 提示词：`system_prompt`, `user_prompt`, `image_prompt`
4. 输出：`output_user`, `output`

**常见错误**：
❌ tab.options 含有 `help: "true"` 字段
❌ batch_variable 放在输出分组（应在第一个无名分组）
❌ 提示词分组缺少 image_prompt
❌ output 字段缺少 global 映射函数
❌ measured.height 设为 700（正确值为 836）

---

### Output 节点
**必需字段**：
- [ ] `message` (type: var_textarea_file, label: "true", required: true)
  - value 格式：`{"msg": "{{#llm_xxx.output#}}", "files": []}`
- [ ] `output_result` (type: output_form, label: "true", 必须包含 options: [])

**常见错误**：
❌ message 的 value 缺少 msg 或 files
❌ output_result 缺少 options: []
❌ message 未引用最终的 LLM 输出

---

### Knowledge Retriever 节点
**必需字段**：
- [ ] `v` 字段为**整数** `2`（不是字符串 `"2"`）
- [ ] `user_question` (type: user_question, label: "true", required: true，含 varZh、help、test、global、linkage)
  - value 必须引用上游变量：`["llm_xxx.output"]`
  - varZh 必须对应说明变量中文名
  - global: `"self=user_prompt"`，linkage: `"retrieved_result"`
- [ ] `knowledge` (type: knowledge_select_multi, label: "true", required: true)
  - 必须使用嵌套结构：`{"type": "knowledge", "value": [...]}`
- [ ] `metadata_filter` (type: metadata_filter, value: {"enabled": false})
- [ ] `advanced_retrieval_switch` (type: search_switch，含 keyword_weight、vector_weight 等)
- [ ] `retrieved_result` (输出字段，type: var，value 为 `[{"key": "retrieved_output", "label": "retrieved_output"}]`)
  - 必须包含 global 映射函数

**常见错误**：
❌ v 字段写成字符串 `"2"`（应为整数 `2`）
❌ knowledge 字段未使用嵌套结构
❌ user_question 缺少 varZh、global、linkage 字段
❌ 缺少 metadata_filter 或 advanced_retrieval_switch
❌ retrieved_result 的 value 写成 `[{"key": "xxx", "label": "检索结果"}]`（label 应为 "retrieved_output"）

---

### Condition 节点
**必需字段**：
- [ ] `condition` (type: condition, label: "true", required: true)
  - `value` 数组中**只放有实际条件的分支**，每个元素包含：
    - `id`: 分支 ID（对应出边的 sourceHandle）
    - `operator`: "and" 或 "or"
    - `conditions`: 条件数组（**不可为空**）
  - 兜底（else）分支**不写入 value 数组**，用 `right_handle` 出边表示

**常见错误**：
❌ 在 value 末尾加 `{"id": "default_branch", "conditions": []}` → 报「条件分支不可为空」
❌ 条件缺少 id 字段（无法连接边）
❌ comparison_operation 使用 equals 匹配 LLM 输出 → 改用 contains
❌ comparison_operation 拼写错误

---

### Tool 节点
**必需字段**：
- [ ] `tool_key` (字符串，如 "web_search")
- [ ] `query` (type: var_textarea, label: "true", required: true)
  - 必须引用输入变量：`"{{#input_xxx.user_input#}}"`
- [ ] `output` (type: var, label: "true", global: "key")

**常见错误**：
❌ tool_key 使用不存在的工具
❌ query 未引用 input 节点的 user_input

## 常用参数取值范围

### LLM 相关参数
| 参数 | 类型 | 范围 | 默认值 | 说明 |
|------|------|------|--------|------|
| temperature | float | [0.0, 2.0] | 0.7 | 控制输出随机性 |
| top_p | float | [0.0, 1.0] | 0.9 | 核采样阈值 |
| max_tokens | int | [1, 100000] | 2048 | 最大生成 token 数 |

### 检索相关参数
| 参数 | 类型 | 范围 | 默认值 | 说明 |
|------|------|------|--------|------|
| keyword_weight | float | [0.0, 1.0] | 0.4 | 关键词检索权重 |
| vector_weight | float | [0.0, 1.0] | 0.6 | 向量检索权重 |
| score_threshold | float | [0.0, 1.0] | 0.6 | 检索分数阈值 |
| max_chunk_size | int | [100, 50000] | 15000 | 最大检索 chunk 大小 |

### 分块相关参数
| 参数 | 类型 | 范围 | 默认值 | 说明 |
|------|------|------|--------|------|
| chunk_size | int | [100, 10000] | 1000 | 分块大小 |
| chunk_overlap | int | [0, 1000] | 100 | 分块重叠大小 |

### 条件判断参数
| 参数 | 类型 | 可选值 |
|------|------|--------|
| comparison_operation | string | equals, not_equals, contains, not_contains, is_empty, is_not_empty, greater_than, less_than |
| operator | string | and, or |

### 注意事项

1. **temperature**: 
   - 0.0-0.3：保守、确定性回答
   - 0.4-0.7：平衡（推荐）
   - 0.8-2.0：创造性、多样性回答

2. **keyword_weight + vector_weight**: 
   - 两者之和应为 1.0

3. **score_threshold**:
   - 0.0-0.3：宽松匹配
   - 0.4-0.7：标准匹配（推荐）

## 检查清单

在导入工作流之前，请检查：

- [ ] 所有 `label` 字段都是 `"true"` 或 `"false"`
- [ ] 所有 `output` 字段都包含 `global` 映射函数
- [ ] `knowledge` 字段使用嵌套结构
- [ ] 变量引用使用 `{{#节点 ID.变量名#}}` 格式
- [ ] JSON 格式正确
