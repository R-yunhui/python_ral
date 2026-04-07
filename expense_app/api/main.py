"""
FastAPI 应用入口

配置并启动个人助手 - 开销管理模块的 API 服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from expense_app.models.database import engine, Base, init_db
from expense_app.api.routers import expenses, incomes, budgets, stats, agent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化数据库表
logger.info("Initializing database tables...")
Base.metadata.create_all(bind=engine)
logger.info("Database tables created")

# 创建 FastAPI 应用实例
app = FastAPI(
    title="Personal Assistant - Expense Module",
    description="个人助手 - 开销管理模块 API",
    version="0.1.0"
)

# 配置 CORS 中间件
# 允许前端应用跨域访问 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 默认端口
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有 HTTP 头
)

# 注册路由
app.include_router(expenses.router)
app.include_router(incomes.router)
app.include_router(budgets.router)
app.include_router(stats.router)
app.include_router(agent.router)

logger.info("API routers registered")


@app.get("/")
def root():
    """
    API 根路径

    Returns:
        dict: API 状态信息
    """
    return {"message": "Personal Assistant API", "status": "running", "version": "0.1.0"}


@app.get("/health")
def health():
    """
    健康检查接口

    Returns:
        dict: 健康状态
    """
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("Personal Assistant API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("Personal Assistant API shutting down...")
