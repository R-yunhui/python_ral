"""
RAG 系统配置模块
统一管理所有存储路径和配置
"""

from pathlib import Path
import os

# 项目根目录（rag 目录）
PROJECT_ROOT = Path(__file__).parent.parent

# ==================== 统一存储目录 ====================
# 所有数据存储在 project_root/rag_data 目录下
STORAGE_ROOT = PROJECT_ROOT / "rag_data"

# 子目录
DB_DIR = STORAGE_ROOT / "database"      # SQLite 数据库
DATA_DIR = STORAGE_ROOT / "documents"   # 上传的文档文件
QDRANT_DIR = STORAGE_ROOT / "qdrant"    # Qdrant 向量数据库
LOG_DIR = STORAGE_ROOT / "logs"         # 日志文件

# 确保目录存在
for dir_path in [DB_DIR, DATA_DIR, QDRANT_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ==================== 数据库配置 ====================
# SQLite 数据库文件
DB_PATH = DB_DIR / "rag.db"
DB_URL = f"sqlite:///{DB_PATH}"

# ==================== Qdrant 配置 ====================
# Qdrant 向量数据库存储路径
QDRANT_PATH = str(QDRANT_DIR)

# ==================== 文档存储配置 ====================
# 文档存储根目录
DOCUMENTS_ROOT = DATA_DIR

# ==================== 其他配置 ====================
# 支持的文档类型
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

# 文档处理配置
CHUNK_SIZE = 512      # 文本分块大小
CHUNK_OVERLAP = 50    # 分块重叠

# Embedding 模型配置
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIMENSION = 1024  # DashScope text-embedding-v3 维度

# LLM 配置
DEFAULT_LLM_MODEL = os.getenv("QWEN_CHAT_MODEL", "qwen-plus")

# 向量相似度配置
DEFAULT_TOP_K = 3         # 默认检索文档数
MAX_TOP_K = 10           # 最大检索文档数


def _env_bool(key: str, default: bool = True) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


# RAG：检索前是否用 LLM 将用户问题改写为更适合向量检索的查询（环境变量 RAG_QUERY_REWRITE，默认开启）
RAG_QUERY_REWRITE_ENABLED = _env_bool("RAG_QUERY_REWRITE", True)

# ==================== 辅助函数 ====================

def get_document_storage_path(kb_id: int) -> Path:
    """获取指定知识库的文档存储路径"""
    storage_path = DOCUMENTS_ROOT / f"kb_{kb_id}"
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


def get_collection_name(kb_id: int) -> str:
    """生成知识库的 Qdrant 集合名称"""
    return f"kb_{kb_id}"


def print_storage_info():
    """打印存储信息"""
    print("=" * 60)
    print("RAG 系统存储配置")
    print("=" * 60)
    print(f"存储根目录：{STORAGE_ROOT}")
    print(f"  ├─ 数据库：{DB_PATH}")
    print(f"  ├─ 文档文件：{DOCUMENTS_ROOT}")
    print(f"  └─ 向量数据库：{QDRANT_PATH}")
    print("=" * 60)
