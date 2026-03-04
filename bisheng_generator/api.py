"""毕昇工作流生成器 - FastAPI 接口"""

# ========== 必须在所有 import 之前设置 UTF-8 编码 ==========
import sys
import io

# 解决 Windows 控制台中文乱码问题：强制设置标准输出为 UTF-8
if sys.platform == "win32":
    # Windows 系统需要特殊处理
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", line_buffering=True
    )
    # 设置环境变量，让后续的子进程也使用 UTF-8
    import os

    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

import logging
from typing import Optional, AsyncGenerator
import json
from pathlib import Path
from asyncio import Queue

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from contextlib import asynccontextmanager

from config.config import config
from core.graph import WorkflowOrchestrator
from main import save_workflow
from models.progress import ProgressEvent, ProgressEventType


# 配置日志 - 使用 UTF-8 编码的 StreamHandler
class UTF8StreamHandler(logging.StreamHandler):
    """自定义 StreamHandler，确保使用 UTF-8 编码"""

    def __init__(self, stream=None):
        super().__init__(stream)
        # 设置编码器为 UTF-8
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - [%(filename)s:%(lineno)d] - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def emit(self, record):
        """重写 emit 方法，确保使用 UTF-8 编码输出"""
        try:
            msg = self.format(record)
            stream = self.stream
            # 确保使用 UTF-8 编码
            if isinstance(stream, io.TextIOWrapper):
                stream.write(msg + self.terminator)
            else:
                # 如果流不是 TextIOWrapper，尝试直接写入
                stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


# 配置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, config.log_level))

# 移除所有已有的 handler
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# 添加我们的 UTF-8 handler
utf8_handler = UTF8StreamHandler(sys.stdout)
root_logger.addHandler(utf8_handler)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """FastAPI 生命周期。知识库改为按请求从 Cookie token 加载，不再启动时预加载。"""
    yield


# 创建 FastAPI 应用
app = FastAPI(
    title="毕昇工作流生成器 API",
    description="提供工作流生成、查看和下载的 API 接口",
    version="0.2.0",
    lifespan=lifespan,
)

# 配置 CORS（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录（用于前端页面）
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


class GenerateRequest(BaseModel):
    """生成请求模型"""

    query: str
    config: Optional[dict] = None


class GenerateResponse(BaseModel):
    """生成响应模型"""

    status: str
    message: str
    workflow: Optional[dict] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    try:
        html_path = static_path / "index.html"
        if html_path.exists():
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return HTMLResponse(
                content="<h1>前端页面未找到</h1><p>请确保 static/index.html 文件存在</p>",
                status_code=404,
            )
    except Exception as e:
        logger.exception(f"读取前端页面失败：{e}")
        raise HTTPException(status_code=500, detail=f"读取页面失败：{str(e)}")


def _get_access_token(request: Request) -> str:
    """从请求 Cookie 取 token（正式环境由前端登录后携带）。"""
    return request.cookies.get("access_token_cookie") or ""


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_workflow(request: GenerateRequest, fastapi_request: Request):
    """
    生成工作流

    Args:
        request: 生成请求，包含用户查询
        fastapi_request: FastAPI 请求对象，用于读取 Cookie 中的 token

    Returns:
        生成的工作流
    """
    token = _get_access_token(fastapi_request)
    logger.info("收到生成请求，query=%s，has_token=%s", request.query[:50], bool(token))

    try:
        orchestrator = WorkflowOrchestrator(request.config)
        await orchestrator.knowledge_agent.load_knowledge_catalog(
            base_url=config.bisheng_base_url,
            access_token=token,
        )

        # 生成工作流
        result = await orchestrator.generate(request.query)

        if result.get("status") == "success":
            # 保存工作流
            workflow = result.get("workflow")
            if workflow:
                filepath = save_workflow(workflow)
                result["file_path"] = str(filepath)
                logger.info(f"工作流已保存：{filepath}")

            return GenerateResponse(**result)
        else:
            return GenerateResponse(
                status="error",
                message=result.get("message", "生成失败"),
                error=result.get("message"),
            )

    except Exception as e:
        logger.error(f"生成工作流失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")


@app.get("/api/workflows", response_model=list)
async def list_workflows():
    """获取已生成的工作流列表"""
    try:
        output_path = Path("output")
        if not output_path.exists():
            return []

        workflows = []
        for file in sorted(output_path.glob("workflow_*.json"), reverse=True):
            workflows.append(
                {
                    "filename": file.name,
                    "filepath": str(file),
                    "created_at": file.stat().st_mtime,
                    "size": file.stat().st_size,
                }
            )

        return workflows
    except Exception as e:
        logger.exception(f"获取工作流列表失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败：{str(e)}")


@app.get("/api/workflow/{filename}")
async def get_workflow(filename: str):
    """获取指定工作流详情"""
    try:
        filepath = Path("output") / filename
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        with open(filepath, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        return {"filename": filename, "workflow": workflow}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"读取工作流失败：{e}")
        raise HTTPException(status_code=500, detail=f"读取失败：{str(e)}")


@app.get("/api/download/{filename}")
async def download_workflow(filename: str):
    """下载工作流文件"""
    try:
        filepath = Path("output") / filename
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        with open(filepath, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        return JSONResponse(
            content=workflow,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"下载工作流失败：{e}")
        raise HTTPException(status_code=500, detail=f"下载失败：{str(e)}")


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "version": "0.2.0"}


@app.post("/api/generate/stream")
@app.get("/api/generate/stream")  # 同时支持 GET 请求（用于浏览器直接访问）
async def generate_workflow_stream(
    fastapi_request: Request,
    request: Optional[GenerateRequest] = None,
    query: Optional[str] = None,
):
    """
    生成工作流（流式 SSE 版本）

    Args:
        request: 生成请求，包含用户查询（POST 方式）
        query: 查询参数（GET 方式）

    Returns:
        SSE 事件流，实时推送进度
    """
    # 兼容 GET 和 POST 请求
    user_query = ""
    request_config = None

    if request:
        user_query = request.query
        request_config = request.config
    elif query:
        user_query = query
        request_config = None
    else:
        user_query = ""

    if not user_query:
        error_event = ProgressEvent(
            event_type=ProgressEventType.ERROR,
            message="缺少查询参数",
            error="请提供 query 参数",
            progress=0.0,
        )
        async def error_generator():
            yield f"event: error\ndata: {json.dumps(error_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")

    logger.info("收到流式生成请求，query=%s", user_query[:50])

    # 创建事件队列
    event_queue = Queue()

    # 定义进度回调函数
    async def progress_callback(event: ProgressEvent):
        """将进度事件放入队列"""
        await event_queue.put(event)

    # 定义 SSE 生成器
    async def event_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 事件"""
        try:
            start_event = ProgressEvent.create_start_event(user_query)
            yield f"data: {json.dumps(start_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            token = _get_access_token(fastapi_request)
            logger.info("流式生成任务启动，query=%s，has_token=%s", user_query[:50], bool(token))
            generate_task = asyncio.create_task(
                run_generation(
                    user_query,
                    request_config,
                    progress_callback,
                    access_token=token,
                    base_url=config.bisheng_base_url,
                )
            )

            while True:
                task_done = generate_task.done()

                while not event_queue.empty():
                    try:
                        event = event_queue.get_nowait()
                        yield f"data: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                    except asyncio.QueueEmpty:
                        break

                if task_done:
                    try:
                        result = generate_task.result()
                        # 如果成功，发送 COMPLETE 确认事件
                        if result.get("status") == "success":
                            final_event = ProgressEvent(
                                event_type=ProgressEventType.COMPLETE,
                                message="生成完成",
                                data=result,
                                progress=100.0,
                            )
                            yield f"data: {json.dumps(final_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                    except Exception as e:
                        logger.exception(f"获取任务结果失败：{e}")
                    break

                # 任务未完成，等待新事件
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 超时后进入下一次循环，检查 task_done
                    continue
                except asyncio.CancelledError:
                    logger.warning("SSE 连接被取消")
                    break
                except Exception as e:
                    logger.exception(f"SSE 事件发送失败：{e}")
                    break

        except Exception as e:
            logger.error(f"SSE 生成器错误：{e}", exc_info=True)
            error_event = ProgressEvent(
                event_type=ProgressEventType.ERROR,
                message=f"生成失败：{str(e)}",
                error=str(e),
                progress=0.0,
            )
            # 标准 SSE 格式
            yield f"data: {json.dumps(error_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"

    # 返回 SSE 响应
    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx: 禁用缓冲
            "Transfer-Encoding": "chunked",
        },
    )

    # 确保响应不会被缓冲
    from starlette.background import BackgroundTask

    async def cleanup():
        """清理函数"""
        pass

    response.background = BackgroundTask(cleanup)
    return response


async def run_generation(
    query: str,
    config: Optional[dict],
    progress_callback,
    access_token: Optional[str] = None,
    base_url: str = "",
) -> dict:
    """
    执行生成任务

    Args:
        query: 用户查询
        config: 配置
        progress_callback: 进度回调
        access_token: 毕昇 access_token（Cookie 或配置），用于按用户加载知识库
        base_url: 毕昇 API base_url，用于拉取知识库列表

    Returns:
        生成结果
    """
    logger.info("run_generation 开始，query=%s", query[:50])
    try:
        orchestrator = WorkflowOrchestrator(
            config_obj=config, progress_callback=progress_callback
        )
        await orchestrator.knowledge_agent.load_knowledge_catalog(
            base_url=base_url,
            access_token=access_token or "",
        )

        result = await orchestrator.generate_with_progress(
            user_input=query, progress_callback=progress_callback
        )

        if result.get("status") == "success":
            workflow = result.get("workflow")
            if workflow:
                filepath = save_workflow(workflow)
                result["file_path"] = str(filepath)
                logger.info("工作流已保存，path=%s", filepath)
        return result

    except Exception as e:
        logger.error(f"生成工作流失败：{e}", exc_info=True)
        return {"status": "error", "message": f"生成失败：{str(e)}"}


# 需要导入 asyncio
import asyncio


def main():
    """启动 FastAPI 服务"""
    import uvicorn

    print("=" * 60)
    print("毕昇工作流生成器 API 服务 v0.2.0")
    print("=" * 60)
    print(f"访问地址：http://localhost:8000")
    print(f"API 文档：http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=config.log_level.lower())


if __name__ == "__main__":
    main()
