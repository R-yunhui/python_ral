# 毕昇工作流 JSON 字段格式规范

验证字段格式时读取本文件。常见导入报错 "Cannot read properties of undefined (reading 'map')" 通常由字段格式不符合平台预期导致。

## label 字段格式

❌ 错误：`"label": "开场白"` — 中文描述，平台无法解析
✅ 正确：`"label": "true"` — 布尔字符串，搭配 `"placeholder": "true"`

## 各类型字段的正确格式

### 文本/数字字段
```json
{"key": "system_prompt", "type": "var_textarea", "label": "true", "value": "提示词内容"}
```

### 开关字段
```json
{"key": "output_user", "type": "switch", "label": "true", "value": true}
```

### 列表字段
```json
{"key": "guide_question", "type": "input_list", "label": "true", "value": ["问题 1", "问题 2"], "placeholder": "true"}
```

### 变量字段
```json
{"key": "user_input", "type": "var", "label": "true", "global": "key"}
```

## output 字段格式

❌ 错误：缺少 `global` 映射
```json
{"key": "output", "type": "var", "value": []}
```

✅ 正确：必须包含 `global` 映射函数
```json
{"key": "output", "type": "var", "label": "true", "value": [], "global": "code:value.map(el => ({ label: el.label, value: el.key }))"}
```

## knowledge 字段格式

❌ 错误：缺少嵌套 `type`
```json
{"key": "knowledge", "value": [{"key": 6, "label": "知识库名称"}]}
```

✅ 正确：嵌套结构含 `type: "knowledge"`
```json
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
}
```

## 常用参数取值范围

### LLM 参数
| 参数 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| temperature | [0.0, 2.0] | 0.7 | 0-0.3 保守，0.4-0.7 平衡（推荐），0.8-2.0 创造性 |
| top_p | [0.0, 1.0] | 0.9 | 核采样阈值 |
| max_tokens | [1, 100000] | 2048 | 最大生成 token 数 |

### 检索参数
| 参数 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| keyword_weight | [0.0, 1.0] | 0.4 | 关键词检索权重（与 vector_weight 之和为 1.0） |
| vector_weight | [0.0, 1.0] | 0.6 | 向量检索权重 |
| max_chunk_size | [100, 50000] | 15000 | 最大检索 chunk 大小 |

### 条件判断
| 参数 | 可选值 |
|------|--------|
| comparison_operation | equals, not_equals, contains, not_contains, is_empty, is_not_empty, greater_than, less_than |
| operator | and, or |

## 导入前检查清单

- [ ] 所有 `label` 字段都是 `"true"` 或 `"false"`
- [ ] 所有 `output` 字段都包含 `global` 映射函数
- [ ] `knowledge` 字段使用嵌套结构
- [ ] 变量引用使用 `{{#节点ID.变量名#}}` 格式
- [ ] JSON 格式正确，可被解析
