# 毕昇工作流生成器 Skill

专业的毕昇 (BiSheng) 工作流 JSON 文件自动生成工具。

## 目录结构

```
bisheng-workflow-generator/
├── SKILL.md                          # 主文件（约 520 行，已精简）
├── README.md                         # 本文件
├── examples/                         # 示例工作流
│   ├── example-simple-qa.json        # 简单问答工作流
│   └── example-knowledge-retrieval.json  # 知识库检索工作流
└── references/                       # 参考文档
    └── field-format-spec.md          # 字段格式规范（约 360 行，已精简）
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
- ✅ 多节点支持：支持 start、input、output、llm、condition、knowledge_retriever、tool 等节点
- ✅ 智能连接：自动生成节点间的 edges 连接关系
- ✅ 参数配置：智能推荐模型参数、提示词配置
- ✅ 规范格式：严格遵循毕昇工作流 JSON 规范
- ✅ 动态布局：根据节点高度动态计算布局，避免重叠

## 支持的节点类型

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

## 常见错误

### ❌ Cannot read properties of undefined (reading 'map')

**原因**: JSON 字段格式不符合毕昇平台预期

**解决方案**: 
1. 检查 `label` 字段是否为 `"true"` 而不是中文
2. 检查 `output` 字段是否包含 `global` 映射函数
3. 检查 `knowledge` 字段是否使用嵌套结构

详见：[字段格式规范](references/field-format-spec.md)

## 文档说明

### SKILL.md（主文档）

**精简后约 520 行**（原 734 行，精简 30%），包含：
- 核心功能介绍
- 使用方法
- JSON 结构详解
- 所有节点类型详解（精简示例）
- Edges 边连接定义
- Position 布局规则
- 注意事项和常见错误
- 质量标准

### references/field-format-spec.md

**精简后约 360 行**（原 573 行，精简 37%），包含：
- label 字段格式（最常见错误）
- 各类型字段的必需属性
- output/knowledge 字段特殊格式
- 各节点必填字段校验清单
- 常用参数取值范围
- 检查清单

### examples/

示例工作流文件（可直接导入测试）：
- `example-simple-qa.json`: 简单问答工作流
- `example-knowledge-retrieval.json`: 知识库检索工作流

## 精简说明

**文档精简策略**：
- ✅ 删除重复内容（workflow-structure.md 已合并到 SKILL.md）
- ✅ 压缩节点示例（从 200-300 行压缩到 50-80 行）
- ✅ 删除内部 UI 配置字段（l2、info、show 等）
- ✅ 删除 position 和 measured 字段（运行时自动计算）
- ✅ 保留所有核心字段和规则

**精简效果**：
- 总行数：从 2036 行 → 880 行（减少 **57%**）
- 文件数：从 4 个 → 3 个
- 生成质量：不受影响（核心信息已保留）

## 版本

当前版本：v2.0.0 (2026-03-02) - 精简版

## 技术支持

- 毕昇 GitHub: https://github.com/dataelement/bisheng
- 毕昇官网：https://www.bisheng.ai
- 毕昇文档：https://docs.bisheng.ai
