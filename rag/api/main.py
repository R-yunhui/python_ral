"""
FastAPI 主应用入口
RAG 知识库问答系统
"""

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from rag.models.database import init_db
from rag.api.routers import kb_router, doc_router, chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    yield


# 创建 FastAPI 应用
app = FastAPI(
    title="RAG 知识库问答系统",
    description="基于 FastAPI + Vue.js + SQLite + Qdrant 的 RAG 知识库问答系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件目录
STATIC_DIR = Path(__file__).parent.parent / "static"

# 挂载静态文件
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 注册 API 路由
app.include_router(kb_router)
app.include_router(doc_router)
app.include_router(chat_router)


@app.get("/", response_class=FileResponse)
async def root():
    """返回前端页面"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "RAG 知识库问答系统 API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)