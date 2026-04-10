# 如何提高 rag 的首字响应速度
import os
import asyncio
import time
import inspect
import re
from pathlib import Path
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from dotenv import load_dotenv

# langchain
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from pydantic import BaseModel
from enum import Enum

# llama_index
from llama_index.core import (
    Document,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.embeddings.langchain import LangchainEmbedding

load_dotenv()

# 重写模型
rewrite_model = ChatOpenAI(
    model=os.getenv("QWEN_FLASH_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
    extra_body={
        "enable_thinking": False,
    },
)

embedding_model = DashScopeEmbeddings(
    model=os.getenv("EMBEDDING_MODEL"),
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
)

answer_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    streaming=True,
    max_tokens=2048,
    extra_body={
        "enable_thinking": False,
    },
)

llama_embed_model = LangchainEmbedding(langchain_embeddings=embedding_model)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_DIR = PROJECT_ROOT / "interview"
INDEX_DIR = Path(__file__).resolve().parent / "rag_index"
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "5"))
REWRITE_CACHE_SIZE = int(os.getenv("RAG_REWRITE_CACHE_SIZE", "256"))
ANSWER_CACHE_SIZE = int(os.getenv("RAG_ANSWER_CACHE_SIZE", "128"))
_RETRIEVER = None
_RETRIEVER_LOCK = asyncio.Lock()
_BM25_RETRIEVER = None
_REWRITE_CACHE: "OrderedDict[str, str]" = OrderedDict()
_REWRITE_CACHE_LOCK = asyncio.Lock()
_ANSWER_CACHE: "OrderedDict[str, str]" = OrderedDict()
_ANSWER_CACHE_LOCK = asyncio.Lock()

# 闲聊意图关键词
_CHITCHAT_KEYWORDS = {
    "你好",
    "hi",
    "hello",
    "hey",
    "谢谢",
    "感谢",
    "thanks",
    "再见",
    "bye",
    "goodbye",
    "拜拜",
    "晚安",
    "早",
    "早上好",
    "在吗",
    "在不在",
    "哈喽",
    "hihi",
}
_CHITCHAT_SHORT_MAX = 3

# 意图分类模型（轻模型）
intent_model = ChatOpenAI(
    model=os.getenv("QWEN_FLASH_MODEL") or "qwen-turbo",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    extra_body={"enable_thinking": False},
)


class IntentType(str, Enum):
    CHITCHAT = "chitchat"  # 闲聊、问候、感谢
    KNOWLEDGE_QA = "knowledge_qa"  # 知识库问答
    OUT_OF_SCOPE = "out_of_scope"  # 超出知识库范围


class IntentResult(BaseModel):
    intent: IntentType
    reason: str


# 意图分类器
intent_classifier = intent_model.with_structured_output(
    IntentResult, method="json_mode"
)

QUERY_REWRITE_SYSTEM = """你是检索查询改写助手。用户会提出与知识库相关的问题。
请将问题改写为更适合向量语义检索的查询：可补充省略的主语或对象，用文档中更可能出现的术语替换口语，去掉无意义的语气词。
要求：
- 只输出改写后的一句检索查询，不要解释、不要加「改写：」等前缀
- 若原问题已经简洁明确，可保持原意或只做轻微润色
- 使用与用户相同的语言（用户用中文则输出中文）"""

ANSWER_SYSTEM_PROMPT = """你是 Java 面试知识库问答助手，请基于检索上下文回答。

规则：
1) 只能依据上下文内容回答，不要编造。
2) 若上下文不足以回答，明确回复“根据当前资料无法确定”，并说明缺失信息。
3) 回答尽量结构化、简洁、可面试表达（先结论，再关键点）。
4) 回答末尾给出“参考来源”列表，展示 source 与 section。"""


F = TypeVar("F", bound=Callable[..., Any])


def time_cost(func: F | None = None, *, name: str | None = None):
    """方法耗时装饰器，支持 sync/async。

    用法:
    - @time_cost
    - @time_cost(name="构建索引")
    """

    def _decorator(target: F) -> F:
        label = name or target.__name__

        if inspect.iscoroutinefunction(target):

            @wraps(target)
            async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                try:
                    return await target(*args, **kwargs)
                finally:
                    elapsed_time = (time.perf_counter() - start_time) * 1000
                    print(f"{label} 耗时: {elapsed_time:.2f} ms")

            return cast(F, _async_wrapper)

        @wraps(target)
        def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                return target(*args, **kwargs)
            finally:
                elapsed_time = (time.perf_counter() - start_time) * 1000
                print(f"{label} 耗时: {elapsed_time:.2f} ms")

        return cast(F, _sync_wrapper)

    if func is not None:
        return _decorator(func)
    return _decorator


def _normalize_query_for_cache(text: str) -> str:
    # 轻量归一化，让“同义空白/大小写差异”的问题能命中同一 key
    return re.sub(r"\s+", " ", text.strip()).lower()


async def _get_rewrite_cache(cache_key: str) -> str | None:
    async with _REWRITE_CACHE_LOCK:
        value = _REWRITE_CACHE.get(cache_key)
        if value is None:
            return None
        _REWRITE_CACHE.move_to_end(cache_key)
        return value


async def _set_rewrite_cache(cache_key: str, value: str) -> None:
    async with _REWRITE_CACHE_LOCK:
        _REWRITE_CACHE[cache_key] = value
        _REWRITE_CACHE.move_to_end(cache_key)
        while len(_REWRITE_CACHE) > REWRITE_CACHE_SIZE:
            _REWRITE_CACHE.popitem(last=False)


async def classify_intent(query: str) -> IntentResult:
    """基于 LLM 的意图分类，闲聊直接走 LLM 不走检索。失败时回退到关键词兜底。"""
    try:
        intent_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="""
                判断用户意图属于以下哪类
                - chitchat: 问候、感谢、闲聊、无意义短句（如"你好"、"谢谢"、"你叫什么"、"今天天气不错"）
                - knowledge_qa: 需要查询知识库的业务/专业问题
                - out_of_scope: 明显超出知识库范围（如"帮我写首情诗"、"预测明天股市"、"讲个笑话"）
                用户问题：{query}
                请输出 JSON 格式，包含 intent 和 reason。"""
                ),
                HumanMessage(content=query),
            ]
        )
        chain = intent_prompt | intent_classifier
        return await chain.ainvoke({"query": query})
    except Exception:
        # LLM 分类失败，回退到关键词兜底
        return _fallback_classify(query)


def _fallback_classify(query: str) -> IntentResult:
    """关键词兜底：当 LLM 分类失败时使用。"""
    text = query.lower().strip()
    if len(text) <= _CHITCHAT_SHORT_MAX:
        return IntentResult(intent=IntentType.CHITCHAT, reason="query 过短，关键词兜底")
    for kw in _CHITCHAT_KEYWORDS:
        if kw in text:
            return IntentResult(
                intent=IntentType.CHITCHAT, reason=f"命中闲聊关键词 {kw!r}，兜底"
            )
    return IntentResult(intent=IntentType.KNOWLEDGE_QA, reason="未命中闲聊关键词，兜底")


def merge_rrf(all_nodes_list: list, top_k: int, k: int = 60):
    """多路检索结果合并：RRF（Reciprocal Rank Fusion）融合排序，按 node_id 去重。

    RRF 公式: score = sum(1 / (k + rank_i)) for each route i
    k=60 是经验值，让不同路的结果能公平融合。
    """
    rrf_scores = {}
    for route_idx, nodes in enumerate(all_nodes_list):
        for rank, item in enumerate(nodes, 1):
            nid = item.node.node_id
            rrf_scores[nid] = rrf_scores.get(nid, 0) + 1 / (k + rank)

    # 找出 node_id 对应的 node 对象（取最高 RRF 分数的那路）
    node_map = {}
    for route_idx, nodes in enumerate(all_nodes_list):
        for rank, item in enumerate(nodes, 1):
            nid = item.node.node_id
            score = 1 / (k + rank)
            if nid not in node_map or score > node_map[nid][1]:
                node_map[nid] = (item.node, score)

    # 按 RRF 分数排序，取 top_k
    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    result = []
    for nid, _score in sorted_items[:top_k]:
        node, _ = node_map[nid]
        # 创建一个兼容对象，带 score 属性
        class _ResultItem:
            def __init__(self, node, score):
                self.node = node
                self.score = score
        result.append(_ResultItem(node, rrf_scores[nid]))
    return result


async def _get_answer_cache(cache_key: str) -> str | None:
    async with _ANSWER_CACHE_LOCK:
        value = _ANSWER_CACHE.get(cache_key)
        if value is None:
            return None
        _ANSWER_CACHE.move_to_end(cache_key)
        return value


async def _set_answer_cache(cache_key: str, value: str) -> None:
    async with _ANSWER_CACHE_LOCK:
        _ANSWER_CACHE[cache_key] = value
        _ANSWER_CACHE.move_to_end(cache_key)
        while len(_ANSWER_CACHE) > ANSWER_CACHE_SIZE:
            _ANSWER_CACHE.popitem(last=False)


@time_cost(name="构建索引")
async def save_index():
    if not DOC_DIR.exists():
        raise FileNotFoundError(f"文档目录不存在: {DOC_DIR.resolve()}")

    documents = SimpleDirectoryReader(
        input_dir=str(DOC_DIR),
        recursive=True,
        required_exts=[".md"],
    ).load_data()

    if not documents:
        raise ValueError(f"文档目录为空，没有可索引文档: {DOC_DIR.resolve()}")

    print(f"加载文档完成，文档数量: {len(documents)}")

    markdown_parser = MarkdownNodeParser.from_defaults()
    markdown_nodes = markdown_parser.get_nodes_from_documents(documents)
    if not markdown_nodes:
        raise ValueError("Markdown 解析后没有可用节点")

    print(f"Markdown 解析完成，节点数量: {len(markdown_nodes)}")

    # 先按 Markdown 结构切，再做句级分块，并补充可追溯元数据
    structured_docs = []
    for node in markdown_nodes:
        metadata = dict(node.metadata or {})
        metadata["source"] = metadata.get(
            "file_path", metadata.get("file_name", "unknown")
        )
        metadata["section"] = metadata.get("header_path", "/")
        text = node.get_content(metadata_mode="none").strip()
        if text:
            structured_docs.append(Document(text=text, metadata=metadata))

    splitter = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunk_nodes = splitter.get_nodes_from_documents(structured_docs)
    if not chunk_nodes:
        raise ValueError("分块后没有可用节点")

    index = VectorStoreIndex(
        nodes=chunk_nodes,
        embed_model=llama_embed_model,
    )

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(INDEX_DIR))
    # 索引重建后让缓存失效，需要显式调用 initialize_rag() 重新预热
    global _RETRIEVER
    _RETRIEVER = None
    return index


@time_cost(name="查询改写")
async def rewrite_text(text: str):
    cache_key = _normalize_query_for_cache(text)
    cached = await _get_rewrite_cache(cache_key)
    if cached is not None:
        print("查询改写缓存命中")
        print(f"查询改写结果: {cached}")
        return cached

    rewrite_content = await rewrite_model.ainvoke(
        [
            SystemMessage(content=QUERY_REWRITE_SYSTEM),
            HumanMessage(content=text),
        ]
    )

    rewritten = rewrite_content.content
    await _set_rewrite_cache(cache_key, rewritten)
    print(f"查询改写结果: {rewritten}")
    return rewritten


@time_cost(name="加载检索器")
async def get_retriever():
    if _RETRIEVER is None:
        raise RuntimeError("Retriever 未初始化，请在启动阶段先调用 initialize_rag()")
    return _RETRIEVER


@time_cost(name="加载BM25检索器")
async def get_bm25_retriever():
    if _BM25_RETRIEVER is None:
        raise RuntimeError("BM25 检索器未初始化，请在启动阶段先调用 initialize_rag()")
    return _BM25_RETRIEVER


@time_cost(name="RAG启动预热")
async def initialize_rag(
    similarity_top_k: int = SIMILARITY_TOP_K, rebuild_if_missing: bool = True
):
    global _RETRIEVER

    async with _RETRIEVER_LOCK:
        if (not INDEX_DIR.exists()) and rebuild_if_missing:
            await save_index()
        elif not INDEX_DIR.exists():
            raise FileNotFoundError(f"索引目录不存在: {INDEX_DIR.resolve()}")

        storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_DIR))
        index = load_index_from_storage(
            storage_context=storage_context,
            embed_model=llama_embed_model,
        )
        _RETRIEVER = index.as_retriever(
            similarity_top_k=similarity_top_k,
        )

        # 构建 BM25 关键词检索器
        nodes = index.docstore.docs.values()
        documents = []
        for node in nodes:
            from langchain_core.documents import Document as LCDocument
            documents.append(
                LCDocument(
                    page_content=node.get_content(metadata_mode="none"),
                    metadata=node.metadata or {},
                )
            )
        _BM25_RETRIEVER = BM25Retriever.from_documents(documents)
        _BM25_RETRIEVER.k = similarity_top_k

        return _RETRIEVER


def build_context(retrieved_nodes) -> str:
    blocks = []
    for i, item in enumerate(retrieved_nodes, start=1):
        node = item.node
        metadata = node.metadata or {}
        source = metadata.get("source", "unknown")
        section = metadata.get("section", "/")
        score = item.score if item.score is not None else 0.0
        content = node.get_content(metadata_mode="none").strip()
        blocks.append(
            f"[片段{i}] score={score:.4f}\nsource={source}\nsection={section}\n内容:\n{content}"
        )
    return "\n\n".join(blocks)


@time_cost(name="LLM生成回答")
async def answer_with_langchain(question: str, context: str) -> None:
    user_prompt = f"""问题：{question}

检索上下文：
{context}

请基于上下文给出最终中文回答。"""
    start_time = time.perf_counter()
    first_token_ms = None
    chunks = []

    async for chunk in answer_model.astream(
        [
            SystemMessage(content=ANSWER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
    ):
        text = chunk.content
        if isinstance(text, list):
            text = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in text
            )
        if not text:
            continue

        if first_token_ms is None:
            first_token_ms = (time.perf_counter() - start_time) * 1000
            print(f"首字响应耗时: {first_token_ms:.2f} ms")

        print(text, end="", flush=True)
        chunks.append(text)

    if first_token_ms is None:
        print("首字响应耗时: 无有效token")
    total_time = time.perf_counter() - start_time
    full_text = "".join(chunks)
    char_count = len(full_text)
    speed = (char_count / total_time) if total_time > 0 else 0
    print(
        f"\n[生成统计] 总字数: {char_count} | 生成速度: {speed:.1f} 字/秒 | 总耗时: {total_time*1000:.2f} ms"
    )
    return full_text


@time_cost(name="检索知识库")
async def get_context(rewritten_query: str) -> str:
    retriever = await get_retriever()
    retrieved_nodes = await retriever.aretrieve(rewritten_query)
    if not retrieved_nodes:
        return "根据当前资料无法确定（未检索到相关内容）。"
    context = build_context(retrieved_nodes)
    return context


async def direct_chitchat_reply(question: str) -> None:
    """闲聊直接走 LLM，不走检索。"""
    print("[意图识别] 闲聊模式，直接回复")
    async for chunk in answer_model.astream([HumanMessage(content=question)]):
        text = chunk.content
        if isinstance(text, list):
            text = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in text
            )
        if not text:
            continue
        print(text, end="", flush=True)
    print()


@time_cost(name="RAG问答")
async def rag_chat(question: str) -> None:
    # 1. 意图识别：闲聊或超出范围的不走检索
    intent = await classify_intent(question)
    print(f"[意图识别] {intent.intent.value} ({intent.reason})")

    if intent.intent == IntentType.CHITCHAT:
        await direct_chitchat_reply(question)
        return

    if intent.intent == IntentType.OUT_OF_SCOPE:
        print("这个问题超出了我的知识范围，我可以帮您查询业务知识、流程规范等。")
        return

    cache_key = _normalize_query_for_cache(question)

    # 2. 检查完整回答缓存
    cached_answer = await _get_answer_cache(cache_key)
    if cached_answer is not None:
        print("[回答缓存命中]")
        print(cached_answer)
        return

    # 3. 并行：改写查询 + 原始查询向量检索 + BM25 关键词检索
    rewrite_task = asyncio.create_task(rewrite_text(question))
    vector_retriever = await get_retriever()
    bm25_retriever = await get_bm25_retriever()

    raw_vector_task = asyncio.create_task(vector_retriever.aretrieve(question))
    bm25_task = asyncio.create_task(bm25_retriever.aget_relevant_documents(question))

    rewritten_query = await rewrite_task
    raw_vector_nodes = await raw_vector_task
    bm25_nodes = await bm25_task

    # 4. 改写后的向量检索
    rewritten_vector_nodes = await vector_retriever.aretrieve(rewritten_query)

    # 5. 三路合并：原始向量 + 改写向量 + BM25，按 node_id 去重，按 RRF 融合排序
    merged_nodes = merge_rrf(
        [raw_vector_nodes, rewritten_vector_nodes, bm25_nodes],
        top_k=SIMILARITY_TOP_K,
    )
    if not merged_nodes:
        context = "根据当前资料无法确定（未检索到相关内容）。"
    else:
        context = build_context(merged_nodes)

    # 6. 生成回答 (stream)
    full_answer = await answer_with_langchain(question, context)

    # 7. 存入回答缓存
    if full_answer:
        await _set_answer_cache(cache_key, full_answer)


async def main():
    await initialize_rag()
    while True:
        question = input("请输入问题: ").strip()
        if question.lower() in ["exit", "quit"]:
            break

        await rag_chat(question)
        print("\n\n")

    print("再见！欢迎下次使用！")


if __name__ == "__main__":

    asyncio.run(main())
