---
name: dify-dsl-generator
description: 专业的 Dify 工作流 DSL/YML 文件生成器，根据用户业务需求自动生成完整的 Dify 工作流配置文件，支持各种节点类型和复杂工作流逻辑
---

# Dify DSL 工作流生成器

专业的 Dify 工作流 DSL/YML 文件自动生成工具，基于对 86+ 实际工作流案例的深度学习，能够根据用户的业务需求自动生成符合 Dify 规范的完整工作流配置文件。

## 核心功能

- ✅ **完整DSL生成**: 自动生成包含 app、dependencies、workflow 的完整 YML 文件
- ✅ **多节点支持**: 支持 start、llm、answer、code、http-request、if-else、tool、knowledge-retrieval 等所有节点类型
- ✅ **智能连接**: 自动生成节点间的 edges 连接关系
- ✅ **参数配置**: 智能推荐模型参数、提示词配置
- ✅ **插件集成**: 自动识别并配置所需的 Dify 插件依赖
- ✅ **规范格式**: 严格遵循 Dify 0.3.0 版本的 DSL 规范

## 使用方法

### 基础用法
```
生成一个 Dify 工作流用于 [业务需求描述]
```

### 详细用法
```
帮我生成一个 Dify 工作流 DSL 文件:
- 功能: [工作流要实现的功能]
- 输入: [用户输入的内容]
- 处理步骤: [详细的处理逻辑]
- 输出: [期望的输出结果]
- 使用插件: [需要的插件，可选]
```

## Dify DSL 文件结构

基于对 86+ 真实工作流案例的学习，Dify DSL YML 文件遵循以下结构:

### 1. App 配置

```yaml
app:
  description: '工作流描述'
  icon: 🤖
  icon_background: '#FFEAD5'
  mode: advanced-chat  # 或 workflow, agent-chat
  name: 工作流名称
  use_icon_as_answer_icon: false
```

**模式说明:**
- `advanced-chat`: 高级对话模式(chatflow)
- `workflow`: 工作流模式
- `agent-chat`: AI Agent 模式

### 2. Dependencies 依赖

```yaml
dependencies:
- current_identifier: null
  type: marketplace
  value:
    marketplace_plugin_unique_identifier: 插件唯一标识符
```

**常用插件:**
- `langgenius/openai_api_compatible`: OpenAI 兼容接口
- `bowenliang123/md_exporter`: Markdown 导出器
- 其他市场插件根据需求添加

### 3. Workflow 工作流

```yaml
kind: app
version: 0.3.0
workflow:
  conversation_variables: []
  environment_variables: []
  features:
    file_upload:
      enabled: false
    speech_to_text:
      enabled: false
    text_to_speech:
      enabled: false
  graph:
    edges: []
    nodes: []
```

## 节点类型详解

### Start 开始节点

```yaml
- data:
    desc: ''
    title: 开始
    type: start
    variables:
    - label: 用户输入
      max_length: 1000
      options: []
      required: true
      type: paragraph  # 或 text-input, select, file
      variable: query
  id: 'start'
  position:
    x: 100
    y: 300
  type: custom
  width: 244
  height: 90
```

**变量类型:**
- `paragraph`: 段落文本(多行)
- `text-input`: 单行文本
- `select`: 下拉选择
- `file`: 文件上传
- `number`: 数字

### LLM 大语言模型节点

```yaml
- data:
    context:
      enabled: false
      variable_selector: []
    model:
      completion_params:
        temperature: 0.7
        max_tokens: 2000
      mode: chat
      name: gpt-4
      provider: openai
    prompt_template:
    - id: 唯一ID
      role: system
      text: 系统提示词
    - id: 唯一ID
      role: user
      text: 用户提示词 {{#变量引用#}}
    title: LLM节点
    type: llm
    vision:
      enabled: false
  id: '节点ID'
  position:
    x: 400
    y: 300
  type: custom
```

**常用模型provider:**
- `openai`: OpenAI
- `langgenius/openai_api_compatible/openai_api_compatible`: 兼容接口
- `anthropic`: Claude
- `alibaba`: 通义千问

**变量引用格式:**
- `{{#节点ID.输出变量#}}`: 引用其他节点的输出
- `{{#sys.query#}}`: 引用系统变量(用户输入)
- `{{#节点ID.text#}}`: 引用LLM输出文本

### Code 代码执行节点

```yaml
- data:
    code: |
      import json

      def main(arg1: str, arg2: str) -> dict:
          # 处理逻辑
          result = process(arg1, arg2)
          return {
              "result": result,
              "status": "success"
          }
    code_language: python3
    outputs:
      result:
        type: string
      status:
        type: string
    title: 代码执行
    type: code
    variables:
    - value_selector:
      - '前置节点ID'
      - 输出变量
      variable: arg1
  id: '节点ID'
  position:
    x: 700
    y: 300
  type: custom
```

**代码语言:**
- `python3`: Python 3
- `javascript`: JavaScript (部分版本支持)

**输出类型:**
- `string`: 字符串
- `number`: 数字
- `object`: 对象
- `array[string]`: 字符串数组
- `array[number]`: 数字数组
- `array[object]`: 对象数组

### HTTP Request 节点

```yaml
- data:
    authorization:
      config: null
      type: no-auth
    body:
      data: '{"key": "{{#变量#}}"}'
      type: json
    headers: ''
    method: post
    timeout:
      max_connect_timeout: 0
      max_read_timeout: 0
      max_write_timeout: 0
    title: HTTP请求
    type: http-request
    url: https://api.example.com/endpoint
  id: '节点ID'
  position:
    x: 1000
    y: 300
  type: custom
```

**HTTP方法:**
- `get`: GET 请求
- `post`: POST 请求
- `put`: PUT 请求
- `patch`: PATCH 请求
- `delete`: DELETE 请求

**认证类型:**
- `no-auth`: 无认证
- `api-key`: API Key
- `bearer`: Bearer Token

### If-Else 条件判断节点

```yaml
- data:
    cases:
    - case_id: case1
      conditions:
      - comparison_operator: contains
        id: 条件ID
        value: 期望值
        variable_selector:
        - '节点ID'
        - 变量名
      id: case1
      logical_operator: and
    logical_operator: or
    title: 条件判断
    type: if-else
  id: '节点ID'
  position:
    x: 1300
    y: 300
  type: custom
```

**比较运算符:**
- `contains`: 包含
- `not contains`: 不包含
- `is`: 等于
- `is not`: 不等于
- `empty`: 为空
- `not empty`: 不为空

**逻辑运算符:**
- `and`: 与
- `or`: 或

### Tool 工具节点

```yaml
- data:
    provider_id: 工具提供者ID
    provider_name: 工具提供者名称
    provider_type: builtin  # 或 api
    title: 工具调用
    tool_configurations: {}
    tool_label: 工具标签
    tool_name: 工具名称
    tool_parameters:
      参数名:
        type: mixed
        value: '{{#变量#}}'
    type: tool
  id: '节点ID'
  position:
    x: 1600
    y: 300
  type: custom
```

**工具类型:**
- `builtin`: 内置工具(如搜索、天气等)
- `api`: API 工具
- `plugin`: 插件工具

### Answer 直接回复节点

```yaml
- data:
    answer: |
      {{#LLM节点ID.text#}}

      {{#代码节点ID.result#}}
    title: 直接回复
    type: answer
    variables: []
  id: answer
  position:
    x: 1900
    y: 300
  type: custom
```

### Variable Aggregator 变量聚合器节点

```yaml
- data:
    advanced_settings: null
    desc: ''
    groups:
    - group_name: 分组1
      output_type: string
      variables:
      - value_selector:
        - '节点ID'
        - 变量名
        variable: 输出变量名
    title: 变量聚合器
    type: variable-aggregator
  id: '节点ID'
  position:
    x: 2200
    y: 300
  type: custom
```

### Parameter Extractor 参数提取器节点

```yaml
- data:
    instruction: 提取指令说明
    is_array: false
    model:
      completion_params: {}
      mode: chat
      name: gpt-4
      provider: openai
    parameters:
    - description: 参数描述
      name: 参数名
      required: true
      type: string
    query:
    - role: user
      text: '{{#输入变量#}}'
    reasoning_mode: prompt
    title: 参数提取
    type: parameter-extractor
  id: '节点ID'
  position:
    x: 2500
    y: 300
  type: custom
```

### Knowledge Retrieval 知识库检索节点

知识库检索节点用于从已有的知识库中检索与用户查询相关的内容，输出结果可作为 LLM 节点的上下文使用。

```yaml
- data:
    # 查询文本变量选择器（必填）
    query_variable_selector:
      - 'start_node_id'      # 前置节点ID
      - query                # 变量名
    
    # 查询图片变量选择器（可选，用于多模态知识库）
    query_attachment_selector: []
    
    # 知识库 ID 列表（必填）
    dataset_ids:
      - 'knowledge_base_id_1'
      - 'knowledge_base_id_2'
    
    # 检索模式（必填）
    retrieval_mode: multi_way    # multi_way（多路检索）或 one_way（单路检索）
    
    # 多路检索配置
    multiple_retrieval_config:
      top_k: 4                    # 返回结果数量
      score_threshold:            # 相似度阈值（可选，如 0.5）
      reranking_enable: false     # 是否启用重排序
    
    # 单路检索配置（retrieval_mode 为 one_way 时必填）
    single_retrieval_config:
      model:
        provider: openai
        name: gpt-4o
        mode: chat
        completion_params: {}
    
    title: 知识检索
    type: knowledge-retrieval
  id: '节点ID'
  position:
    x: 600
    y: 282
  type: custom
  width: 244
  height: 90
```

**关键字段说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query_variable_selector` | array | ✅ | 查询文本的变量引用，格式 `[节点ID, 变量名]` |
| `dataset_ids` | array | ✅ | 知识库 ID 列表，需在 Dify 中预先创建 |
| `retrieval_mode` | string | ✅ | `multi_way`（多路检索）或 `one_way`（单路检索） |
| `multiple_retrieval_config` | object | 条件 | 多路检索时使用 |
| `single_retrieval_config` | object | 条件 | 单路检索时需配置模型 |

**检索模式说明:**

- `multi_way`（多路检索）: 从多个知识库同时检索，结果合并后重排序
- `one_way`（单路检索）: 使用 LLM 决定从哪个知识库检索，需配置模型

**输出变量:**

知识库检索节点输出 `result` 变量，包含检索到的文档片段数组。

**与 LLM 节点配合使用:**

```yaml
# 在 LLM 节点中引用知识库检索结果作为上下文
- data:
    context:
      enabled: true
      variable_selector:
        - 'knowledge_retrieval_node_id'
        - result
    model:
      # ... 模型配置
    prompt_template:
    - id: system_prompt
      role: system
      text: |
        根据以下知识库内容回答用户问题：
        {{#知识检索节点ID.result#}}
    - id: user_prompt
      role: user
      text: '{{#start.query#}}'
    title: LLM节点
    type: llm
```

**注意事项:**

1. 使用前需在 Dify 中创建知识库并获取 `dataset_id`
2. 知识库 ID 可通过 Dify 控制台的 URL 或 API 获取
3. 多模态知识库需要配置 `query_attachment_selector`
4. 重排序（reranking）需要配置对应的 rerank 模型

## Edges 连接关系

```yaml
edges:
- data:
    isInIteration: false
    isInLoop: false
    sourceType: start
    targetType: llm
  id: 源节点ID-source-目标节点ID-target
  source: '源节点ID'
  sourceHandle: source
  target: '目标节点ID'
  targetHandle: target
  type: custom
  zIndex: 0
```

**连接规则:**
1. 每个节点至多有一个入边(start 节点除外)
2. 节点可以有多个出边(if-else 等分支节点)
3. 最终必须连接到 answer 节点或其他输出节点
4. `sourceType` 和 `targetType` 必须与实际节点类型匹配

## Position 坐标布局

**推荐布局:**
- 起始 X: 100
- 节点间距 X: 300-400
- Y 坐标: 保持在同一水平线(300)或根据分支适当调整
- 分支节点的子节点 Y 坐标: ±150

**示例布局:**
```
Start(100,300) → LLM(400,300) → Code(700,300) → Answer(1000,300)
```

**分支布局:**
```
                    → Branch1(1100,150)
If-Else(800,300) →
                    → Branch2(1100,450)
```

## 生成工作流步骤

### 1. 需求分析
- 理解用户的业务需求
- 确定工作流类型(chatflow/workflow/agent)
- 识别所需的节点类型
- 规划处理流程

### 2. 节点设计
- 设计开始节点的输入变量
- 规划 LLM 节点的提示词
- 确定代码执行逻辑
- 配置 HTTP 请求参数
- 设计输出格式

### 3. 流程连接
- 建立节点间的逻辑关系
- 配置变量传递
- 处理条件分支
- 确保流程闭环

### 4. DSL 生成
- 生成符合规范的 YAML 格式
- 配置唯一的节点 ID
- 设置合理的坐标位置
- 添加必要的依赖插件

### 5. 验证检查
- 检查 YAML 格式正确性
- 验证变量引用完整性
- 确认节点连接合理性
- 检查必填字段完整性

## 实际案例学习

基于 86+ 真实工作流案例的学习总结:

### 案例1: 图片 OCR 识别工作流

**需求**: 上传图片 → OCR 识别 → 提取文字

**节点流程**:
1. Start(file input) →
2. LLM(vision enabled, OCR) →
3. Answer(display result)

**关键配置**:
- Start 节点: type: file, allowed_file_types: [image]
- LLM 节点: vision.enabled: true, vision.configs.variable_selector 指向文件变量
- 系统提示词: "仅输出识别到的图片中的文字信息"

### 案例2: 文本生成 HTML 工作流

**需求**: 文本描述 → 生成HTML代码 → 保存为文件

**节点流程**:
1. Start(text input) →
2. LLM(generate HTML) →
3. Parameter Extractor(extract HTML code) →
4. Tool(md_exporter, save file) →
5. Answer(return file URL)

**关键配置**:
- LLM 提示词: "生成 HTML 程序，仅输出 HTML 代码"
- Parameter Extractor: 提取 HTML 代码块
- Tool: 使用 md_exporter 插件保存文件

### 案例3: 数据查询可视化工作流

**需求**: 用户问题 → SQL 查询 → 图表展示

**节点流程**:
1. Start(query input) →
2. LLM(generate SQL) →
3. HTTP Request(database API) →
4. Code(format data) →
5. LLM(generate chart HTML) →
6. Answer(display chart)

**关键配置**:
- LLM1: Text-to-SQL 生成
- HTTP: 调用数据库查询 API
- Code: 格式化 JSON 数据为图表数据格式
- LLM2: 生成 ECharts/Chart.js HTML

### 案例4: 知识库问答工作流

**需求**: 用户问题 → 知识库检索 → LLM 回答

**节点流程**:
1. Start(query input) →
2. Knowledge Retrieval(search knowledge base) →
3. LLM(answer with context) →
4. Answer(display result)

**关键配置**:
```yaml
# Knowledge Retrieval 节点
- data:
    query_variable_selector:
      - 'start_node_id'
      - query
    dataset_ids:
      - 'your_dataset_id'
    retrieval_mode: multi_way
    multiple_retrieval_config:
      top_k: 4
      score_threshold: 0.5
      reranking_enable: false
    title: 知识检索
    type: knowledge-retrieval

# LLM 节点引用知识库结果
- data:
    context:
      enabled: true
      variable_selector:
        - 'knowledge_retrieval_node_id'
        - result
    prompt_template:
    - role: system
      text: 根据以下知识库内容回答用户问题，如果知识库中没有相关信息请如实告知。
    - role: user
      text: '{{#start.query#}}'
```

### 案例5: AI Agent 工作流

**需求**: 复杂任务 → Agent 自主规划 → 调用工具 → 返回结果

**节点流程**:
1. Start(task input) →
2. LLM(reasoning, with tools) →
3. Multiple Tool nodes(parallel) →
4. Variable Aggregator(collect results) →
5. LLM(summarize) →
6. Answer(final response)

**关键配置**:
- mode: agent-chat
- LLM 配置: 启用多个 tool
- Tool 并行执行: 多个 edges 从 LLM 指向不同 Tool
- Variable Aggregator: 聚合多个 Tool 的输出

## 常用提示词模板

### Text-to-SQL

```
你是一个专业的 SQL 专家。根据用户的自然语言问题生成准确的 SQL 查询语句。

数据库schema:
{{#数据库结构#}}

用户问题: {{#sys.query#}}

要求:
1. 只输出 SQL 语句，不要有其他说明
2. 确保 SQL 语法正确
3. 使用合适的 JOIN 和 WHERE 条件
```

### 数据提取

```
从以下文本中提取指定信息:

文本内容:
{{#输入文本#}}

提取要求:
- 提取所有日期
- 提取所有人名
- 提取所有金额

以 JSON 格式输出:
{
  "dates": [],
  "names": [],
  "amounts": []
}
```

### HTML 生成

```
根据用户需求生成完整的 HTML 页面。

需求: {{#用户需求#}}

要求:
1. 生成完整的 HTML 文档
2. 包含必要的 CSS 样式
3. 添加必要的 JavaScript 交互
4. 确保代码格式规范
5. 只输出 HTML 代码，不要 markdown 代码块标记
```

## 注意事项

### 必须遵守的规则

1. **唯一ID生成**: 每个节点必须有唯一的 ID(建议使用时间戳: `1747991890414`)
2. **变量引用格式**: 必须使用 `{{#节点ID.变量名#}}` 格式
3. **节点类型匹配**: edges 中的 sourceType 和 targetType 必须与节点实际类型一致
4. **必填字段**: 不能省略 YAML 中的必填字段
5. **YAML格式**: 严格遵循 YAML 缩进规范(2空格)

### 常见错误避免

1. ❌ 变量引用错误: `{{节点ID.变量}}`
   ✅ 正确格式: `{{#节点ID.变量#}}`

2. ❌ 缺少节点连接: 节点孤立未连接
   ✅ 确保所有节点都在 edges 中有连接关系

3. ❌ ID 重复: 多个节点使用相同 ID
   ✅ 每个节点使用唯一 ID

4. ❌ Position 重叠: 多个节点坐标相同
   ✅ 合理规划节点位置，避免重叠

5. ❌ 依赖缺失: 使用插件但未在 dependencies 中声明
   ✅ 使用插件时必须添加对应的 dependency

## 输出格式

生成的 DSL 文件必须是完整的、可直接导入 Dify 的 YAML 格式:

```yaml
app:
  # App 配置

dependencies:
  # 依赖列表

kind: app
version: 0.3.0

workflow:
  conversation_variables: []
  environment_variables: []
  features:
    # 功能配置
  graph:
    edges:
      # 连接关系
    nodes:
      # 节点定义
```

## 质量标准

### 合格标准(必达)
- ✅ YAML 格式正确，可以被解析
- ✅ 包含完整的 app、dependencies、workflow 配置
- ✅ 至少包含 start 和 answer 节点
- ✅ 节点间有正确的连接关系
- ✅ 变量引用格式正确
- ✅ 所有必填字段完整

### 优秀标准(建议)
- 🌟 提示词设计专业，符合业务需求
- 🌟 节点布局美观，逻辑清晰
- 🌟 包含适当的错误处理(if-else 判断)
- 🌟 使用合适的插件提升功能
- 🌟 代码执行节点健壮性强
- 🌟 变量命名语义化

## 触发关键词

自动触发 dify-dsl-generator skill 的关键词:
- "生成 Dify 工作流"
- "创建 Dify DSL"
- "Dify YML 文件"
- "工作流配置文件"

## 更新日志

### v1.1.0 (2025-02-27)
- ✅ 新增 Knowledge Retrieval 知识库检索节点支持
- ✅ 添加知识库检索节点的完整 DSL 结构说明
- ✅ 添加知识库检索与 LLM 节点配合使用的示例
- ✅ 新增知识库问答工作流案例

### v1.0.0 (2025-11-22)
- ✅ 初始版本
- ✅ 基于 86+ 真实案例学习
- ✅ 支持所有主要节点类型
- ✅ 完整的 DSL 生成能力
- ✅ 智能节点连接
- ✅ 规范格式输出

## 技术支持

参考资源:
- Dify GitHub: https://github.com/langgenius/dify
- DSL 案例仓库: https://github.com/wwwzhouhui/dify-for-dsl
- Dify 官方文档: https://docs.dify.ai
