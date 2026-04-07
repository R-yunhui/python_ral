"""
应用启动脚本

使用 Uvicorn ASGI 服务器启动 FastAPI 应用
支持自动重载模式，适用于开发环境
"""
import uvicorn
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Starting Personal Assistant API server...")
    logger.info("Server will be available at: http://localhost:8000")
    logger.info("API documentation available at: http://localhost:8000/docs")

    # 启动 Uvicorn 服务器
    # host: 监听地址（0.0.0.0 允许外部访问）
    # port: 监听端口
    # reload: 启用自动重载（开发模式）
    uvicorn.run(
        "expense_app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
