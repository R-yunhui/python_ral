# 毕昇工作流生成器 Skill

专业的毕昇 (BiSheng) 工作流 JSON 文件自动生成工具。

## 目录结构

```
bisheng-workflow-generator/
├── SKILL.md                          # 主文件（1224 行）
├── README.md                         # 本文件
├── examples/                         # 示例工作流
│   ├── example-simple-qa.json        # 简单问答工作流
│   └── example-knowledge-retrieval.json  # 知识库检索工作流
└── references/                       # 详细参考文档
    ├── workflow-structure.md         # 工作流结构详解（729 行）
    └── field-format-spec.md          # 字段格式规范（重要）
```

## 快速开始

### 使用方法

1. **基础用法**
   ```
   生成一个毕昇工作流用于 [业务需求描述]
   ```

2. **详细用法**
   ```
   帮我生成一个毕昇工作流:
   - 功能：[工作流要实现的功能]
   - 输入：[用户输入的内容]
   - 处理步骤：[详细的处理逻辑]
   - 输出：[期望的输出结果]
   - 知识库：[需要的知识库，可选]
   ```

### 导入工作流

1. 登录毕昇平台
2. 进入工作流管理
3. 点击"导入工作流"
4. 选择 JSON 文件上传

## 核心功能

- ✅ 完整工作流生成：自动生成包含 nodes、edges 的完整 JSON 文件
- ✅ 多节点支持：支持所有毕昇节点类型
- ✅ 智能连接：自动生成节点间的 edges 连接关系
- ✅ 参数配置：智能推荐模型参数、提示词配置
- ✅ 规范格式：严格遵循毕昇工作流 JSON 规范

## 支持的节点类型

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

## 常见错误

### ❌ Cannot read properties of undefined (reading 'map')

**原因**: JSON 字段格式不符合毕昇平台预期

**解决方案**: 
1. 检查 `label` 字段是否为 `"true"` 而不是中文
2. 检查 `output` 字段是否包含 `global` 映射函数
3. 检查 `knowledge` 字段是否使用嵌套结构

详见：[字段格式规范](references/field-format-spec.md)

## 文档说明

### SKILL.md

主文档，包含：
- 核心功能介绍
- 使用方法
- JSON 结构详解
- 所有节点类型详解
- Edges 边连接定义
- Position 布局规则
- 实际案例（4 个）
- 常用提示词模板（5 个）
- 注意事项和常见错误
- 质量标准

### references/workflow-structure.md

工作流结构详解，包含：
- 文件结构概览
- 顶层配置详解
- Graph 图结构
- 所有节点类型的完整字段说明
- 变量引用规范
- 坐标系统
- 最佳实践
- 版本兼容性

### references/field-format-spec.md

**重要**：字段格式规范，包含：
- label 字段格式（最常见错误）
- 各类型字段的必需属性
- output 字段格式
- knowledge 字段格式
- varZh 字段说明
- 完整示例
- 检查清单

### examples/

示例工作流文件：
- `example-simple-qa.json`: 简单问答工作流（可直接导入测试）
- `example-knowledge-retrieval.json`: 知识库检索工作流（可直接导入测试）

## 版本

当前版本：v1.0.0 (2026-02-27)

## 技术支持

- 毕昇 GitHub: https://github.com/dataelement/bisheng
- 毕昇官网：https://www.bisheng.ai
- 毕昇文档：https://docs.bisheng.ai
