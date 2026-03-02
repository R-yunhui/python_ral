"""
RAG 知识库问答系统 - 启动脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn

if __name__ == "__main__":
    print("🚀 启动 RAG 知识库问答系统...")
    print("📖 API 文档：http://localhost:8000/docs")
    print("🏠 前端页面：http://localhost:8000")
    print("\n按 Ctrl+C 停止服务\n")
    
    uvicorn.run(
        "rag.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )