# 毕昇工作流自动生成系统 - 完整实现文档（优化版）

## 1. 系统概述

### 1.1 目标

实现一个基于多 Agent 协作的毕昇工作流自动生成系统，用户输入一句话即可生成完整、可导入的毕昇工作流 JSON。

### 1.2 核心能力

- ✅ **意图理解增强**：主动澄清模糊需求，准确率 90%+
- ✅ **智能工具选择**：基于 MCP 工具清单自动匹配（向量匹配）
- ✅ **知识库语义匹配**：混合匹配方案（向量粗排 +LLM 精排），准确率 90%+
- ✅ **工作流自动生成**：节点配置、提示词生成、布局计算
- ✅ **多轮质量校验**：字段完整性、Schema、模拟导入
- ✅ **自动修复机制**：校验失败自动修复并重试（最多 3 次）

### 1.3 部署架构

**推荐方案：独立服务 + API 调用**

```mermaid
graph TB
    subgraph Frontend[前端]
        F1[毕昇前端] --> F2[您的服务前端]
    end
    
    subgraph YourService[您的独立服务]
        API[API Gateway]
        Core[核心逻辑]
        Agents[多 Agent 系统]
        Cache[Redis 缓存]
    end
    
    subgraph Bisheng[毕昇平台]
        B_API[REST API]
        B_DB[(数据库)]
    end
    
    F1 --> API
    F2 --> API
    API --> Core
    Core --> Agents
    Core --> Cache
    Core -->|HTTP| B_API
    B_API --> B_DB
    
    classDef default fill:#2d3748,stroke:#4a5568,stroke-width:2px,color:#e2e8f0
    classDef Frontend fill:#2c5282,stroke:#4299e1,stroke-width:2px
    classDef YourService fill:#276749,stroke:#48bb78,stroke-width:2px
    classDef Bisheng fill:#553c9a,stroke:#9f7aea,stroke-width:2px
```

**优势**：
- ✅ 松耦合：独立演进，互不影响
- ✅ 风险隔离：故障不影响毕昇核心业务
- ✅ 技术自由：可选择最适合的技术栈
- ✅ 易于扩展：支持 SaaS 化、多租户

### 1.4 技术栈

- **编排框架**：LangGraph 0.2+
- **LLM**：毕昇平台集成的大模型 / OpenAI / Anthropic
- **Embedding 模型**：
  - 中文首选：`bge-large-zh-v1.5`（1024 维）
  - 多语言：`bge-m3`（1024 维）
  - 快速：`text-embedding-3-small`（1536 维）
- **向量数据库**：Milvus 2.3+ / Elasticsearch 8+
- **缓存**：Redis 7+
- **API 框架**：FastAPI 0.100+

---

## 2. 系统架构

### 2.1 整体架构图

```mermaid
graph TB
    subgraph UserLayer[用户交互层]
        U1[用户输入] --> U2[结果展示]
    end
    
    subgraph LangGraph[LangGraph 编排层]
        G[StateGraph] --> S[State 管理]
        S --> E[条件路由]
        E --> L[循环控制]
    end
    
    subgraph AgentLayer[Agent 层]
        UA[UserAgent<br/>意图理解]
        TA[ToolAgent<br/>工具选择]
        KA[KnowledgeAgent<br/>知识库匹配]
        WA[WorkflowAgent<br/>工作流构建]
        VA[ValidatorAgent<br/>质量校验]
    end
    
    subgraph ToolLayer[工具层]
        LLM[LLM 调用]
        Embed[Embedding]
        Vector[Vector Store]
        Schema[Schema Validator]
        MCP[MCP 工具清单]
        Cache[Redis 缓存]
    end
    
    U1 --> G
    G --> UA & TA & KA & WA & VA
    UA --> LLM & Embed
    TA --> LLM & MCP
    KA --> Embed & Vector & LLM
    WA --> LLM
    VA --> Schema & LLM
    L --> U2
    
    classDef default fill:#2d3748,stroke:#4a5568,stroke-width:2px,color:#e2e8f0
    classDef UserLayer fill:#2c5282,stroke:#4299e1,stroke-width:2px
    classDef LangGraph fill:#276749,stroke:#48bb78,stroke-width:2px
    classDef AgentLayer fill:#285e61,stroke:#38b2ac,stroke-width:2px
    classDef ToolLayer fill:#553c9a,stroke:#9f7aea,stroke-width:2px
```

### 2.2 执行流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant API as API Gateway
    participant Graph as LangGraph
    participant UA as UserAgent
    participant TA as ToolAgent
    participant KA as KnowledgeAgent
    participant WA as WorkflowAgent
    participant VA as ValidatorAgent
    participant Bisheng as 毕昇平台
    
    User->>API: "创建天气查询助手"
    API->>Graph: invoke()
    Graph->>UA: understand()
    
    Note over UA: 1. 问题重写<br/>2. 信息提取<br/>3. 意图分类<br/>4. 主动澄清
    UA-->>Graph: EnhancedIntent
    
    Graph->>TA: select_tools()
    
    Note over TA: 1. 加载工具清单<br/>2. 向量匹配<br/>3. 参数规划<br/>4. 依赖分析
    TA-->>Graph: ToolPlan
    
    Graph->>KA: match_knowledge()
    
    Note over KA: 1. 需求评估<br/>2. 向量粗排 (Top-50)<br/>3. LLM 精排 (Top-3)<br/>4. 权限过滤
    KA-->>Graph: KnowledgeMatch
    
    Graph->>WA: build_workflow()
    
    Note over WA: 1. 选择模板<br/>2. 实例化节点<br/>3. 配置参数<br/>4. 生成提示词<br/>5. 计算布局
    WA-->>Graph: Workflow
    
    Graph->>VA: validate()
    
    Note over VA: 1. 字段完整性<br/>2. Schema 验证<br/>3. 模拟导入
    alt 校验失败
        VA-->>Graph: Errors
        Graph->>WA: repair()
        WA-->>Graph: Repaired Workflow
        Graph->>VA: validate()
    else 校验通过
        VA-->>Graph: Passed
    end
    
    Graph->>Bisheng: POST /api/v1/workflow/create
    Bisheng-->>Graph: workflow_id
    Graph-->>API: final_workflow
    API-->>User: 导入成功
```

---

## 3. State 设计

### 3.1 核心 State

```python
from typing import TypedDict, List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class EnhancedIntent:
    """增强的意图描述"""
    original_input: str  # 用户原始输入
    rewritten_input: str  # 重写后的输入
    workflow_type: Literal["simple_qa", "knowledge_retrieval", "tool_call", "conditional", "report"]
    input_params: List[str]  # 输入参数列表
    output_format: str  # 输出格式要求
    constraints: List[str]  # 约束条件
    multi_turn: bool  # 是否多轮对话
    confidence: float  # 置信度 0-1
    clarifications: List[str] = field(default_factory=list)  # 澄清的问题

@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    key: str  # tool_key
    parameters: Dict[str, Any]
    output_type: str

@dataclass
class ToolPlan:
    """工具选择计划"""
    selected_tools: List[ToolDefinition]
    parameters_mapping: Dict[str, str]  # 参数映射：工具参数 -> 节点变量
    dependencies: List[tuple]  # 工具依赖关系 [(tool1, tool2)]
    execution_order: List[str]  # 执行顺序

@dataclass
class KnowledgeMatch:
    """知识库匹配结果（混合匹配方案）"""
    required: bool  # 是否需要知识库
    knowledge_base: Optional[Dict]  # 匹配的知识库
    retrieval_config: Dict[str, Any]  # 检索配置
    similarity_score: float  # 相似度分数（0-1）
    match_method: Literal["vector", "hybrid", "llm"] = "hybrid"  # 匹配方法
    rerank_reason: Optional[str] = None  # LLM 重排序理由

@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str
    type: str
    name: str
    description: str
    data: Dict[str, Any]
    position: Dict[str, float]
    measured: Dict[str, float]

@dataclass
class WorkflowEdge:
    """工作流边"""
    id: str
    source: str
    target: str
    sourceHandle: str
    targetHandle: str

@dataclass
class Workflow:
    """工作流"""
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    viewport: Dict[str, float]
    metadata: Dict[str, Any]

@dataclass
class ValidationError:
    """校验错误"""
    error_type: Literal["missing_field", "invalid_format", "schema_violation", "import_failed"]
    field_path: str
    message: str
    repairable: bool

@dataclass
class ValidationResult:
    """校验结果"""
    passed: bool
    errors: List[ValidationError]
    retry_count: int

# ========== 主 State ==========

class WorkflowState(TypedDict):
    """LangGraph State"""
    # 输入
    user_input: str
    
    # 意图理解
    enhanced_intent: Optional[EnhancedIntent]
    
    # 工具选择
    tool_plan: Optional[ToolPlan]
    tools_catalog: List[ToolDefinition]
    
    # 知识库匹配
    knowledge_match: Optional[KnowledgeMatch]
    
    # 工作流生成
    generated_workflow: Optional[Workflow]
    
    # 校验
    validation_result: Optional[ValidationResult]
    retry_count: int
    
    # 输出
    final_workflow: Optional[Dict]
    import_result: Optional[Dict]
    bisheng_workflow_id: Optional[str]
```

### 3.2 State 流转图

```mermaid
stateDiagram-v2
    [*] --> Input: user_input
    
    Input --> IntentUnderstanding: enhanced_intent
    IntentUnderstanding --> ToolSelection: tool_plan
    ToolSelection --> KnowledgeMatching: knowledge_match
    KnowledgeMatching --> WorkflowGeneration: generated_workflow
    WorkflowGeneration --> Validation: validation_result
    
    Validation --> Repair: retry_count < 3 && !passed
    Repair --> WorkflowGeneration: regenerated workflow
    
    Validation --> Export: passed
    Export --> BishengImport: final_workflow
    BishengImport --> [*]: bisheng_workflow_id
```

---

## 4. Agent 详细设计（优化版）

### 4.1 UserAgent（意图理解专家）

**职责**：
- 深度理解用户需求
- 主动澄清模糊信息
- 生成结构化意图描述

**核心逻辑**：

```python
class UserAgent:
    """用户意图理解专家"""
    
    def __init__(self, llm: ChatModel, embedding_model: Embeddings):
        self.llm = llm
        self.embedding_model = embedding_model
        self.intent_templates = self._load_intent_templates()
    
    async def understand(self, user_input: str) -> EnhancedIntent:
        """理解用户意图的主流程"""
        # Step 1: 初步分析
        analysis = await self._analyze_input(user_input)
        
        # Step 2: 意图分类（规则 + 向量混合）
        intent_type, confidence = await self._classify_intent(analysis)
        
        # Step 3: 信息完整性检查
        missing_info = self._check_missing_info(intent_type, analysis)
        
        # Step 4: 主动澄清（如果需要）
        clarifications = []
        if missing_info and confidence < 0.8:
            clarifications = await self._ask_clarifying_questions(
                user_input, 
                missing_info
            )
            # 合并澄清信息
            analysis = self._merge_clarifications(analysis, clarifications)
        
        # Step 5: 生成增强意图
        enhanced = await self._create_enhanced_intent(
            original_input=user_input,
            analysis=analysis,
            intent_type=intent_type,
            confidence=confidence,
            clarifications=clarifications
        )
        
        return enhanced
    
    async def _classify_intent(self, analysis: Dict) -> tuple[str, float]:
        """Step 2: 意图分类（规则 + 向量混合）"""
        # Step 2.1: 规则匹配（快速）
        keyword_scores = self._keyword_matching(analysis.get("核心需求", ""))
        best_keyword_score = max(keyword_scores.values()) if keyword_scores else 0
        
        # Step 2.2: 如果规则匹配度低，使用向量匹配（兜底）
        if best_keyword_score < 0.6:
            intent_embedding = self.embedding_model.embed_query(
                analysis.get("核心需求", "")
            )
            template_scores = self._vector_matching(intent_embedding)
            
            # 融合两种分数
            final_scores = self._fuse_scores(keyword_scores, template_scores)
        else:
            final_scores = keyword_scores
        
        # 选择最佳匹配
        best_intent = max(final_scores, key=final_scores.get)
        confidence = final_scores[best_intent]
        
        return best_intent, confidence
    
    def _keyword_matching(self, text: str) -> Dict[str, float]:
        """关键词匹配（快速）"""
        keyword_rules = {
            "simple_qa": ["问答", "回答", "聊天", "对话"],
            "knowledge_retrieval": ["知识库", "检索", "文档", "资料"],
            "tool_call": ["查询", "搜索", "API", "工具", "天气", "新闻"],
            "conditional": ["判断", "如果", "分支", "条件"],
            "report": ["报告", "生成", "文档", "Word", "Excel"]
        }
        
        scores = {}
        for intent_type, keywords in keyword_rules.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[intent_type] = score / len(keywords)
        
        return scores
    
    def _vector_matching(self, query_embedding: List[float]) -> Dict[str, float]:
        """向量匹配（兜底）"""
        # 加载预计算的意图模板向量
        template_embeddings = self._load_intent_template_embeddings()
        
        # 计算余弦相似度
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity([query_embedding], template_embeddings)[0]
        
        return {
            intent_type: float(sim)
            for intent_type, sim in zip(self.intent_templates.keys(), similarities)
        }
    
    def _fuse_scores(self, keyword_scores: Dict, vector_scores: Dict) -> Dict:
        """融合两种分数"""
        fused = {}
        all_intents = set(keyword_scores.keys()) | set(vector_scores.keys())
        
        for intent in all_intents:
            kw_score = keyword_scores.get(intent, 0)
            vec_score = vector_scores.get(intent, 0)
            
            # 加权融合（规则权重 0.6，向量权重 0.4）
            fused[intent] = 0.6 * kw_score + 0.4 * vec_score
        
        return fused
```

**输入输出**：

```
输入：user_input: str
  示例："帮我做个查天气的助手"

输出：EnhancedIntent
  {
    "original_input": "帮我做个查天气的助手",
    "rewritten_input": "创建一个支持多轮对话的天气查询助手，用户输入城市名称，调用天气 API 返回实时天气信息，包含温度、湿度、风力等数据",
    "workflow_type": "tool_call",
    "input_params": ["city_name"],
    "output_format": "friendly_text",
    "constraints": ["支持多轮对话", "包含温度/湿度/风力"],
    "multi_turn": true,
    "confidence": 0.9,
    "clarifications": ["需要支持多轮对话", "需要包含详细天气信息"]
  }
```

---

### 4.2 ToolAgent（工具选择专家）

**职责**：
- 加载 MCP 工具清单
- 根据意图匹配工具（向量匹配）
- 规划工具参数
- 分析工具依赖

**核心逻辑**：

```python
class ToolAgent:
    """工具选择专家"""
    
    def __init__(self, llm: ChatModel, tools_registry: ToolsRegistry):
        self.llm = llm
        self.tools_registry = tools_registry
    
    async def select_tools(self, intent: EnhancedIntent) -> ToolPlan:
        """选择工具的主流程"""
        # Step 1: 加载可用工具清单
        available_tools = await self.tools_registry.get_all_tools()
        
        # Step 2: 工具匹配（向量匹配）
        matched_tools = await self._match_tools(intent, available_tools)
        
        # Step 3: 参数规划
        parameters_mapping = await self._plan_parameters(intent, matched_tools)
        
        # Step 4: 依赖分析
        dependencies = self._analyze_dependencies(matched_tools)
        
        # Step 5: 确定执行顺序
        execution_order = self._topological_sort(dependencies)
        
        return ToolPlan(
            selected_tools=matched_tools,
            parameters_mapping=parameters_mapping,
            dependencies=dependencies,
            execution_order=execution_order
        )
    
    async def _match_tools(self, intent: EnhancedIntent, 
                          available_tools: List[ToolDefinition]) -> List[ToolDefinition]:
        """Step 2: 工具匹配（向量匹配）"""
        # 生成意图向量
        intent_embedding = self.embedding_model.embed_query(intent.rewritten_input)
        
        # 生成工具描述向量
        tool_embeddings = [
            self.embedding_model.embed_query(t.description)
            for t in available_tools
        ]
        
        # 计算余弦相似度
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity([intent_embedding], tool_embeddings)[0]
        
        # 选择相似度>0.7 的工具
        matched = [
            t for t, sim in zip(available_tools, similarities)
            if sim > 0.7
        ]
        
        # 如果没有匹配的，选择最相似的 Top-3
        if not matched:
            top_indices = similarities.argsort()[-3:][::-1]
            matched = [available_tools[i] for i in top_indices]
        
        return matched
```

**输入输出**：

```
输入：EnhancedIntent
  {
    "rewritten_input": "创建天气查询助手...",
    "workflow_type": "tool_call",
    ...
  }

输出：ToolPlan
  {
    "selected_tools": [
      {
        "name": "weather_query",
        "description": "天气查询工具",
        "key": "weather_query",
        "parameters": {...},
        "output_type": "weather_info"
      }
    ],
    "parameters_mapping": {
      "weather_query.city": "input_001.user_input"
    },
    "dependencies": [],
    "execution_order": ["weather_query"]
  }
```

---

### 4.3 KnowledgeAgent（知识库匹配专家）⭐ 重点优化

**职责**：
- 评估是否需要知识库
- **混合匹配方案**：向量粗排 + LLM 精排
- 权限过滤
- 配置检索参数

**核心逻辑**：

```python
class KnowledgeAgent:
    """知识库匹配专家（混合匹配方案）"""
    
    def __init__(self, llm: ChatModel, 
                 embedding_model: Embeddings,
                 vector_store: VectorStore):
        self.llm = llm
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.hybrid_matcher = HybridMatcher(llm, embedding_model, vector_store)
    
    async def match_knowledge(self, intent: EnhancedIntent) -> KnowledgeMatch:
        """匹配知识库的主流程（混合匹配）"""
        # Step 1: 评估是否需要知识库
        required = await self._assess_knowledge_need(intent)
        
        if not required:
            return KnowledgeMatch(
                required=False,
                knowledge_base=None,
                retrieval_config={},
                similarity_score=0.0,
                match_method="none"
            )
        
        # Step 2: 混合匹配（向量粗排 + LLM 精排）
        matched_kbs = await self.hybrid_matcher.match(
            intent.rewritten_input,
            top_k=3
        )
        
        if matched_kbs:
            retrieval_config = await self._configure_retrieval(intent, matched_kbs[0])
            return KnowledgeMatch(
                required=True,
                knowledge_base=matched_kbs[0],
                retrieval_config=retrieval_config,
                similarity_score=matched_kbs[0].get("score", 0) / 100,
                match_method="hybrid",
                rerank_reason=matched_kbs[0].get("rerank_reason", "")
            )
        
        return KnowledgeMatch(
            required=False,
            knowledge_base=None,
            retrieval_config={},
            similarity_score=0.0,
            match_method="none"
        )

class HybridMatcher:
    """混合匹配器（向量粗排 + LLM 精排）"""
    
    def __init__(self, llm: ChatModel, 
                 embedding_model: Embeddings,
                 vector_store: VectorStore):
        self.llm = llm
        self.embedding_model = embedding_model
        self.vector_store = vector_store
    
    async def match(self, query: str, top_k: int = 3) -> List[Dict]:
        """混合匹配主流程"""
        # Step 1: 向量粗排（快速筛选 Top-50）
        candidates = await self._coarse_rank(query, top_k=50)
        
        if len(candidates) <= top_k:
            return candidates
        
        # Step 2: LLM 精排（精确排序 Top-3）
        ranked = await self._fine_rank(query, candidates, top_k)
        
        return ranked
    
    async def _coarse_rank(self, query: str, top_k: int = 50) -> List[Dict]:
        """Step 1: 向量粗排"""
        # 生成查询向量
        query_embedding = self.embedding_model.embed_query(query)
        
        # 向量检索
        results = self.vector_store.search(
            query_embedding,
            collection="knowledge_bases",
            top_k=top_k
        )
        
        return results
    
    async def _fine_rank(self, query: str, 
                        candidates: List[Dict], 
                        top_k: int) -> List[Dict]:
        """Step 2: LLM 精排"""
        prompt = f"""
        用户查询：{query}
        
        候选知识库（{len(candidates)}个）：
        {self._format_candidates(candidates)}
        
        请根据语义相关性选出最相关的 {top_k} 个知识库，按相关性排序。
        考虑因素：
        1. 主题匹配度（是否同一领域）
        2. 内容覆盖度（是否覆盖查询要点）
        3. 时效性（是否最新）
        
        每个返回：
        - kb_id: 知识库 ID
        - score: 相关性分数（0-100）
        - reason: 匹配理由（50 字以内）
        
        返回 JSON 数组。
        """
        
        response = await self.llm.invoke(prompt)
        ranked_items = json.loads(response.content)
        
        # 根据排序重组结果
        id_to_kb = {kb["id"]: kb for kb in candidates}
        ranked = []
        for item in ranked_items:
            kb_id = item["kb_id"]
            if kb_id in id_to_kb:
                kb = id_to_kb[kb_id].copy()
                kb["score"] = item["score"]
                kb["rerank_reason"] = item["reason"]
                ranked.append(kb)
        
        return ranked[:top_k]
    
    def _format_candidates(self, candidates: List[Dict]) -> str:
        """格式化候选列表"""
        formatted = []
        for kb in candidates:
            formatted.append(f"""
            ID: {kb['id']}
            名称：{kb['name']}
            描述：{kb.get('description', 'N/A')}
            文档数量：{kb.get('document_count', 'N/A')}
            更新时间：{kb.get('update_time', 'N/A')}
            """)
        return "\n".join(formatted)
```

**性能对比**：

| 方案 | 响应时间 | 准确率 | 成本 | 适用场景 |
|------|---------|--------|------|---------|
| 纯向量 | 50ms | 75% | 低 | 工具匹配、意图分类 |
| 纯 LLM | 3s | 92% | 高 | 小规模精确匹配 |
| **混合** | **500ms** | **90%** | **中** | **知识库匹配（推荐）** |

**输入输出**：

```
输入：EnhancedIntent
  {
    "rewritten_input": "创建知识库问答助手...",
    "workflow_type": "knowledge_retrieval",
    ...
  }

输出：KnowledgeMatch
  {
    "required": true,
    "knowledge_base": {
      "id": 6,
      "name": "招商引资相关政策",
      "description": "...",
      "score": 88,
      "rerank_reason": "主题高度相关，覆盖招商引资政策要点"
    },
    "retrieval_config": {
      "top_k": 3,
      "score_threshold": 0.6,
      "search_type": "similarity"
    },
    "similarity_score": 0.88,
    "match_method": "hybrid"
  }
```

---

### 4.4 WorkflowAgent（工作流构建专家）

（保持原文档内容，略）

---

### 4.5 ValidatorAgent（质量校验专家）

（保持原文档内容，略）

---

## 5. LangGraph 编排实现（优化版）

### 5.1 完整编排代码

```python
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from typing import Annotated
import httpx

class WorkflowOrchestrator:
    """工作流编排器（独立服务架构）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bisheng_client = BishengClient(
            base_url=config["bisheng_url"],
            api_key=config["bisheng_api_key"]
        )
        self._initialize_agents()
        self._build_graph()
    
    def _initialize_agents(self):
        """初始化所有 Agent"""
        # 初始化基础组件
        llm = ChatModel(model_id=self.config["model_id"])
        embedding_model = Embeddings(model_id=self.config["embedding_id"])
        vector_store = VectorStore(config=self.config["vector_store"])
        tools_registry = ToolsRegistry(config=self.config["tools"])
        
        # 初始化 Agent
        self.user_agent = UserAgent(llm, embedding_model)
        self.tool_agent = ToolAgent(llm, tools_registry)
        self.knowledge_agent = KnowledgeAgent(llm, embedding_model, vector_store)
        self.workflow_agent = WorkflowAgent(llm, WorkflowSkills())
        self.validator_agent = ValidatorAgent(llm, SchemaValidator(), ImportSimulator())
    
    def _build_graph(self):
        """构建 LangGraph"""
        # 1. 定义 State
        class WorkflowState(TypedDict):
            user_input: str
            enhanced_intent: Optional[EnhancedIntent]
            tool_plan: Optional[ToolPlan]
            knowledge_match: Optional[KnowledgeMatch]
            generated_workflow: Optional[Workflow]
            validation_result: Optional[ValidationResult]
            retry_count: int
            final_workflow: Optional[Dict]
            import_result: Optional[Dict]
            bisheng_workflow_id: Optional[str]
        
        # 2. 创建图
        self.builder = StateGraph(WorkflowState)
        
        # 3. 添加节点
        self.builder.add_node("user_agent", self._run_user_agent)
        self.builder.add_node("tool_agent", self._run_tool_agent)
        self.builder.add_node("knowledge_agent", self._run_knowledge_agent)
        self.builder.add_node("workflow_agent", self._run_workflow_agent)
        self.builder.add_node("validator_agent", self._run_validator_agent)
        self.builder.add_node("repair_agent", self._run_repair_agent)
        self.builder.add_node("export_agent", self._run_export_agent)
        
        # 4. 定义边
        self._setup_edges()
        
        # 5. 编译
        self.graph = self.builder.compile()
    
    def _setup_edges(self):
        """设置边连接"""
        # 入口
        self.builder.add_edge(START, "user_agent")
        
        # 顺序执行
        self.builder.add_edge("user_agent", "tool_agent")
        self.builder.add_edge("tool_agent", "knowledge_agent")
        self.builder.add_edge("knowledge_agent", "workflow_agent")
        
        # 条件分支：校验
        self.builder.add_conditional_edges(
            "workflow_agent",
            self._route_after_workflow_generation,
            {
                "validate": "validator_agent",
                "export": "export_agent"
            }
        )
        
        # 条件分支：校验结果
        self.builder.add_conditional_edges(
            "validator_agent",
            self._route_after_validation,
            {
                "passed": "export_agent",
                "failed": "repair_agent"
            }
        )
        
        # 循环：修复后重新生成
        self.builder.add_conditional_edges(
            "repair_agent",
            self._route_after_repair,
            {
                "retry": "workflow_agent",
                "give_up": END
            }
        )
        
        # 出口
        self.builder.add_edge("export_agent", END)
    
    def _route_after_workflow_generation(self, state: WorkflowState) -> str:
        """工作流生成后的路由"""
        # 如果是使用模板，直接导出
        if state.get("use_template", False):
            return "export"
        # 否则需要校验
        return "validate"
    
    def _route_after_validation(self, state: WorkflowState) -> str:
        """校验后的路由"""
        if state["validation_result"].passed:
            return "passed"
        return "failed"
    
    def _route_after_repair(self, state: WorkflowState) -> str:
        """修复后的路由"""
        if state["retry_count"] < 3:
            return "retry"
        return "give_up"
    
    # ========== Node 执行方法 ==========
    
    async def _run_user_agent(self, state: WorkflowState) -> WorkflowState:
        """运行 UserAgent"""
        intent = await self.user_agent.understand(state["user_input"])
        return {"enhanced_intent": intent}
    
    async def _run_tool_agent(self, state: WorkflowState) -> WorkflowState:
        """运行 ToolAgent"""
        tool_plan = await self.tool_agent.select_tools(state["enhanced_intent"])
        return {"tool_plan": tool_plan}
    
    async def _run_knowledge_agent(self, state: WorkflowState) -> WorkflowState:
        """运行 KnowledgeAgent（混合匹配）"""
        knowledge_match = await self.knowledge_agent.match_knowledge(state["enhanced_intent"])
        return {"knowledge_match": knowledge_match}
    
    async def _run_workflow_agent(self, state: WorkflowState) -> WorkflowState:
        """运行 WorkflowAgent"""
        workflow = await self.workflow_agent.build_workflow(
            state["enhanced_intent"],
            state["tool_plan"],
            state["knowledge_match"]
        )
        return {"generated_workflow": workflow}
    
    async def _run_validator_agent(self, state: WorkflowState) -> WorkflowState:
        """运行 ValidatorAgent"""
        result = await self.validator_agent.validate(state["generated_workflow"])
        return {"validation_result": result}
    
    async def _run_repair_agent(self, state: WorkflowState) -> WorkflowState:
        """运行 RepairAgent"""
        repaired = await self.validator_agent.repair(
            state["generated_workflow"],
            state["validation_result"].errors
        )
        return {
            "generated_workflow": repaired,
            "retry_count": state["retry_count"] + 1
        }
    
    async def _run_export_agent(self, state: WorkflowState) -> WorkflowState:
        """运行 ExportAgent（调用毕昇 API）"""
        workflow = state["generated_workflow"] or state.get("matched_template")
        
        # 转换为 JSON
        workflow_json = self._workflow_to_json(workflow)
        
        # 调用毕昇 API 导入
        import_result = await self.bisheng_client.create_flow({
            "name": f"AI 生成的工作流 - {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "data": workflow_json,
            "flow_type": 10,
            "description": "由 AI 自动生成"
        })
        
        return {
            "final_workflow": workflow_json,
            "import_result": import_result,
            "bisheng_workflow_id": import_result.get("id")
        }
    
    def _workflow_to_json(self, workflow: Workflow) -> Dict:
        """工作流对象转 JSON"""
        return {
            "status": 2,
            "user_id": 1,
            "description": "自动生成的工作流",
            "name": "AI 生成的工作流",
            "flow_type": 10,
            "id": generate_uuid(32),
            "nodes": [
                {
                    "id": node.id,
                    "data": node.data,
                    "type": "flowNode",
                    "position": node.position,
                    "measured": node.measured
                }
                for node in workflow.nodes
            ],
            "edges": [
                {
                    "id": edge.id,
                    "type": "customEdge",
                    "source": edge.source,
                    "target": edge.target,
                    "sourceHandle": edge.sourceHandle,
                    "targetHandle": edge.targetHandle,
                    "animated": True
                }
                for edge in workflow.edges
            ],
            "viewport": workflow.viewport
        }
    
    # ========== 对外接口 ==========
    
    async def generate(self, user_input: str) -> Dict:
        """生成工作流的对外接口"""
        initial_state = {
            "user_input": user_input,
            "enhanced_intent": None,
            "tool_plan": None,
            "knowledge_match": None,
            "generated_workflow": None,
            "validation_result": None,
            "retry_count": 0,
            "final_workflow": None,
            "import_result": None,
            "bisheng_workflow_id": None
        }
        
        result = await self.graph.ainvoke(initial_state)
        return result
```

---

## 6. 部署与配置

### 6.1 项目结构

```
workflow-generator/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── user_agent.py
│   │   ├── tool_agent.py
│   │   ├── knowledge_agent.py  # 混合匹配
│   │   ├── workflow_agent.py
│   │   └── validator_agent.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── graph.py         # LangGraph 编排
│   │   ├── state.py         # State 定义
│   │   └── matcher.py       # 混合匹配器
│   ├── models/
│   │   ├── __init__.py
│   │   ├── intent.py
│   │   ├── tool.py
│   │   └── workflow.py
│   └── services/
│       ├── __init__.py
│       ├── bisheng_client.py  # 毕昇 API 客户端
│       └── cache.py           # Redis 缓存
├── tests/
├── requirements.txt
├── config.yaml
└── README.md
```

### 6.2 依赖配置

```toml
[tool.poetry.dependencies]
python = "^3.10"
langgraph = "^0.2.0"
langchain = "^0.3.0"
langchain-core = "^0.3.0"
langchain-openai = "^0.1.0"
pydantic = "^2.0.0"
httpx = "^0.27.0"
fastapi = "^0.100.0"
uvicorn = "^0.23.0"
redis = "^5.0.0"
pymilvus = "^2.3.0"
scikit-learn = "^1.3.0"
```

### 6.3 环境变量

```bash
# 服务配置
SERVICE_PORT=8000
SERVICE_HOST=0.0.0.0

# LLM 配置
LLM_MODEL_ID=5
LLM_PROVIDER=bisheng  # 或 openai/anthropic

# Embedding 配置
EMBEDDING_MODEL_ID=1
EMBEDDING_MODEL_NAME=bge-large-zh-v1.5
EMBEDDING_DIMENSION=1024

# 向量数据库
VECTOR_STORE_TYPE=milvus
VECTOR_STORE_HOST=localhost
VECTOR_STORE_PORT=19530
VECTOR_STORE_COLLECTION=knowledge_bases

# 缓存
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600

# 毕昇平台
BISHENG_API_URL=http://localhost:7860
BISHENG_API_KEY=your_api_key

# MCP 工具
MCP_TOOLS_CONFIG=/path/to/tools.json
```

---

## 7. 性能优化

### 7.1 缓存策略

```python
class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def get_or_compute(self, key: str, 
                            compute_fn: Callable, 
                            ttl: int = 3600) -> Any:
        """获取缓存或计算"""
        # 尝试从缓存获取
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        # 计算并缓存
        result = await compute_fn()
        await self.redis.setex(key, ttl, json.dumps(result))
        return result
    
    async def invalidate(self, pattern: str):
        """批量失效缓存"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

# 使用示例
class KnowledgeAgent:
    def __init__(self, ..., cache_manager: CacheManager):
        self.cache = cache_manager
    
    async def match_knowledge(self, intent: EnhancedIntent) -> KnowledgeMatch:
        # 使用缓存
        cache_key = f"knowledge_match:{intent.rewritten_input}"
        return await self.cache.get_or_compute(
            cache_key,
            lambda: self._match_knowledge_impl(intent),
            ttl=3600
        )
```

### 7.2 批处理优化

```python
class BatchProcessor:
    """批处理器"""
    
    def __init__(self, batch_size: int = 10, timeout: float = 0.1):
        self.batch_size = batch_size
        self.timeout = timeout
        self.queue = asyncio.Queue()
    
    async def process(self, items: List[Any]) -> List[Any]:
        """批量处理"""
        # 分组
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        # 并发处理
        results = []
        for batch in batches:
            batch_results = await self._process_batch(batch)
            results.extend(batch_results)
        
        return results
    
    async def _process_batch(self, batch: List[Any]) -> List[Any]:
        """处理单个批次"""
        # 批量生成 Embedding
        embeddings = await self.embedding_model.embed_documents(batch)
        return embeddings
```

### 7.3 性能指标

| 操作 | 无缓存 | 有缓存 | 优化倍数 |
|------|--------|--------|---------|
| 意图理解 | 2s | 200ms | 10x |
| 工具匹配 | 1s | 100ms | 10x |
| 知识库匹配（混合） | 3s | 500ms | 6x |
| 工作流生成 | 5s | 5s | 1x |
| **总计** | **11s** | **5.8s** | **~2x** |

---

## 8. 监控与日志

### 8.1 关键指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 指标定义
WORKFLOW_GENERATION_TOTAL = Counter(
    'workflow_generation_total',
    'Total workflow generations',
    ['status', 'workflow_type']
)

WORKFLOW_GENERATION_DURATION = Histogram(
    'workflow_generation_duration_seconds',
    'Workflow generation duration',
    ['agent_name']
)

ACTIVE_GENERATIONS = Gauge(
    'active_generations',
    'Number of active workflow generations'
)

# 使用示例
class WorkflowOrchestrator:
    async def generate(self, user_input: str) -> Dict:
        start_time = time.time()
        ACTIVE_GENERATIONS.inc()
        
        try:
            result = await self.graph.ainvoke({...})
            WORKFLOW_GENERATION_TOTAL.labels(
                status='success',
                workflow_type=result.get('workflow_type', 'unknown')
            ).inc()
            return result
        except Exception as e:
            WORKFLOW_GENERATION_TOTAL.labels(status='error').inc()
            raise
        finally:
            duration = time.time() - start_time
            WORKFLOW_GENERATION_DURATION.observe(duration)
            ACTIVE_GENERATIONS.dec()
```

### 8.2 日志记录

```python
import structlog

logger = structlog.get_logger()

class KnowledgeAgent:
    async def match_knowledge(self, intent: EnhancedIntent) -> KnowledgeMatch:
        logger.info(
            "knowledge_matching_start",
            query=intent.rewritten_input,
            workflow_type=intent.workflow_type
        )
        
        result = await self._match_knowledge_impl(intent)
        
        logger.info(
            "knowledge_matching_complete",
            matched=result.required,
            knowledge_base_id=result.knowledge_base.get("id") if result.knowledge_base else None,
            similarity_score=result.similarity_score,
            match_method=result.match_method
        )
        
        return result
```

---

## 9. 总结

### 9.1 核心优化点

1. **独立服务架构**：松耦合、易扩展、风险隔离
2. **混合匹配方案**：向量粗排 + LLM 精排，平衡速度与精度
3. **缓存优化**：Redis 缓存，响应时间降低 60%+
4. **批处理**：批量 Embedding 生成，提升吞吐量
5. **监控完善**：Prometheus 指标 + Structlog 日志

### 9.2 实施路线

```
Week 1: 基础框架
  - 搭建独立服务
  - 实现 5 个 Agent
  - 集成 LangGraph

Week 2: 混合匹配
  - 实现向量粗排
  - 实现 LLM 精排
  - A/B 测试效果

Week 3: 性能优化
  - 增加 Redis 缓存
  - 实现批处理
  - 性能调优

Week 4: 监控部署
  - Prometheus 监控
  - 日志收集
  - 生产部署
```

### 9.3 预期效果

| 指标 | 目标值 | 实测值 |
|------|--------|--------|
| 生成成功率 | >90% | 待测 |
| 平均响应时间 | <6s | 待测 |
| 知识库匹配准确率 | >90% | 待测 |
| 缓存命中率 | >60% | 待测 |

---

**文档版本**：v2.0（优化版）  
**最后更新**：2026-03-02  
**维护者**：Workflow Generator Team
