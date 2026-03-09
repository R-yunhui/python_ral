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
import time
import uuid
from typing import Optional, AsyncGenerator
import json
from pathlib import Path
from asyncio import Queue

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from contextlib import asynccontextmanager

import asyncio

from config.config import config
from config.logging_config import setup_logging
from core.graph import WorkflowOrchestrator
from core.workflow_io import save_workflow
from models.progress import ProgressEvent, ProgressEventType, AgentName
from services.bisheng_import_service import do_import_workflow
from services.session_timeline_service import (
    save_timeline_message,
    save_timeline_progress_event,
    list_sessions as list_sessions_svc,
    get_session_timeline as get_session_timeline_svc,
)

# 日志在独立模块配置，避免 api 内堆积
setup_logging(
    log_level=config.log_level,
    log_dir=getattr(config, "log_dir", None) or "",
    repo_root=Path(__file__).resolve().parent.parent,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """FastAPI 生命周期：MySQL 已配置时自动创建表。"""
    if config.is_mysql_configured():
        from db.database import init_db
        init_db(config)
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
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    is_resume: bool = Field(default=False, alias="isResume")
    original_query: Optional[str] = Field(default=None, alias="originalQuery")

    model_config = {"populate_by_name": True}


class GenerateResponse(BaseModel):
    """生成响应模型"""

    status: str
    message: str
    workflow: Optional[dict] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None
    file_path: Optional[str] = None
    import_result: Optional[dict] = None
    import_error: Optional[str] = None
    session_id: Optional[str] = None
    needs_clarification: bool = False
    pending_clarification: Optional[dict] = None


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


# ========== 会话历史（时间线）API ==========


@app.get("/api/sessions")
async def get_sessions(limit: int = 100):
    """
    获取会话列表，按最后活动时间倒序。
    仅当 MySQL 已配置时返回数据，否则返回空列表。
    """
    sessions = list_sessions_svc(config, limit=limit)
    return sessions


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str, limit: int = 500):
    """
    获取某会话的完整时间线（对话消息 + 推送的进度事件）。
    仅当 MySQL 已配置时返回数据，否则返回空列表。
    """
    timeline = get_session_timeline_svc(config, session_id, limit=limit)
    return {"session_id": session_id, "timeline": timeline}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_workflow(request: GenerateRequest, fastapi_request: Request):
    """
    生成工作流（支持首轮 / 续轮澄清）

    Args:
        request: 生成请求，包含用户查询、session_id、is_resume
        fastapi_request: FastAPI 请求对象，用于读取 Cookie 中的 token

    Returns:
        生成的工作流或澄清请求
    """
    token = _get_access_token(fastapi_request)
    session_id = request.session_id or uuid.uuid4().hex
    is_resume = request.is_resume

    logger.info(
        "收到生成请求，query=%s, session_id=%s, is_resume=%s, has_token=%s",
        request.query[:50],
        session_id,
        is_resume,
        bool(token),
    )

    # 续轮校验
    if is_resume and not request.session_id:
        raise HTTPException(status_code=400, detail="续轮请求必须携带 sessionId")
    if is_resume and (not request.query or not request.query.strip()):
        raise HTTPException(status_code=400, detail="请输入补充信息")

    graph_config = {"configurable": {"thread_id": session_id}}

    try:
        orchestrator = WorkflowOrchestrator(request.config)
        # 知识库在知识库匹配节点内惰性加载，此处不再预加载
        if is_resume:
            result = await orchestrator.generate_resume(
                resume_value=request.query,
                session_id=session_id,
                config=graph_config,
                bisheng_base_url=config.bisheng_base_url,
                access_token=token,
            )
        else:
            result = await orchestrator.generate(
                user_input=request.query,
                session_id=session_id,
                config=graph_config,
                bisheng_base_url=config.bisheng_base_url,
                access_token=token,
            )

        # 需要澄清 → 直接返回，不保存/导入
        if result.get("needs_clarification"):
            return GenerateResponse(
                status="success",
                message=result.get("message", "需要用户补充信息"),
                session_id=session_id,
                needs_clarification=True,
                pending_clarification=result.get("pending_clarification"),
            )

        if result.get("status") == "success":
            workflow = result.get("workflow")
            if workflow:
                filepath = save_workflow(workflow)
                result["file_path"] = str(filepath)
                logger.info("工作流已保存：%s", filepath)

            auto_import = (request.config or {}).get("auto_import", False)
            if auto_import and workflow:
                try:
                    import_result = await do_import_workflow(
                        workflow,
                        config.bisheng_base_url,
                        token,
                        metadata=result.get("metadata"),
                        publish=True,
                    )
                    result["import_result"] = import_result
                    logger.info(
                        "工作流已导入毕昇：flow_id=%s", import_result.get("flow_id")
                    )
                except Exception as e:
                    result["import_error"] = str(e)
                    logger.warning("导入毕昇失败：%s", e)

            result["session_id"] = session_id
            return GenerateResponse(**result)
        else:
            return GenerateResponse(
                status="error",
                message=result.get("message", "生成失败"),
                error=result.get("message"),
                session_id=session_id,
            )

    except Exception as e:
        error_msg = str(e)
        # 续轮 session 失效
        if is_resume and (
            "thread" in error_msg.lower() or "checkpoint" in error_msg.lower()
        ):
            raise HTTPException(status_code=409, detail="会话已过期，请重新发起")
        logger.error("生成工作流失败：%s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败：{error_msg}")


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


class ImportWorkflowRequest(BaseModel):
    """手动导入工作流到毕昇的请求体"""

    workflow: Optional[dict] = None
    """工作流 JSON，与 filename 二选一"""
    filename: Optional[str] = None
    """已保存的工作流文件名（如 workflow_123.json），与 workflow 二选一"""
    name: Optional[str] = None
    """工作流名称，不传则用 workflow 内的 name 或默认「导入的工作流」"""
    publish: bool = True
    """是否创建后立即上线"""


@app.post("/api/workflow/import")
async def import_workflow_to_bisheng(
    body: ImportWorkflowRequest,
    fastapi_request: Request,
):
    """
    将工作流导入到毕昇平台（手动调用）。
    需在 Cookie 中携带 access_token_cookie（前端登录后由毕昇写入）。
    """
    token = _get_access_token(fastapi_request)
    workflow = None
    if body.workflow:
        workflow = body.workflow
    elif body.filename:
        filepath = Path("output") / body.filename
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在：{body.filename}")
        with open(filepath, "r", encoding="utf-8") as f:
            workflow = json.load(f)
    else:
        raise HTTPException(
            status_code=400,
            detail="请提供 workflow（JSON）或 filename（已保存的文件名）",
        )
    if not workflow or not workflow.get("nodes") or not workflow.get("edges"):
        raise HTTPException(
            status_code=400, detail="工作流格式无效：需包含 nodes 和 edges"
        )
    try:
        result = await do_import_workflow(
            workflow,
            config.bisheng_base_url,
            token,
            explicit_name=body.name,
            publish=body.publish,
        )
        return {"status": "success", "message": "已导入到毕昇", "import_result": result}
    except Exception as e:
        logger.warning("导入毕昇失败：%s", e)
        raise HTTPException(status_code=502, detail=f"导入失败：{str(e)}")


@app.post("/api/generate/stream")
@app.get("/api/generate/stream")
async def generate_workflow_stream(
    fastapi_request: Request,
    request: Optional[GenerateRequest] = None,
    query: Optional[str] = None,
):
    """
    生成工作流（流式 SSE 版本，支持首轮/续轮澄清）

    Args:
        request: 生成请求，包含用户查询（POST 方式）
        query: 查询参数（GET 方式）

    Returns:
        SSE 事件流，实时推送进度
    """
    user_query = ""
    request_config = None
    session_id = None
    is_resume = False
    original_user_input = None

    if request:
        user_query = request.query
        request_config = request.config
        session_id = request.session_id
        is_resume = request.is_resume
        original_user_input = request.original_query
    else:
        user_query = query or ""
        # GET 时从 query_params 读取 session_id、is_resume、original_query
        params = fastapi_request.query_params
        if params.get("session_id"):
            session_id = params.get("session_id")
        if params.get("is_resume", "").lower() in ("true", "1", "yes"):
            is_resume = True
        if params.get("original_query"):
            original_user_input = params.get("original_query")

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

    session_id = session_id or uuid.uuid4().hex

    logger.info(
        "收到流式生成请求，query=%s, session_id=%s, is_resume=%s",
        user_query[:50],
        session_id,
        is_resume,
    )

    # 写入当前轮用户消息到会话时间线（仅当 MySQL 已配置时）
    if config.is_mysql_configured():
        try:
            save_timeline_message(config, session_id, "user", user_query)
        except Exception as e:
            logger.warning("写入会话用户消息失败（不影响生成）: %s", e)

    event_queue: Queue = Queue()

    async def progress_callback(event: ProgressEvent):
        await event_queue.put(event)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            start_event = ProgressEvent.create_start_event(user_query)
            if config.is_mysql_configured():
                try:
                    save_timeline_progress_event(
                        config, session_id, start_event.model_dump(mode="json")
                    )
                except Exception as e:
                    logger.warning("写入会话进度事件失败: %s", e)
            yield f"data: {json.dumps(start_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)

            token = _get_access_token(fastapi_request)
            logger.info(
                "流式生成任务启动，query=%s, session_id=%s, is_resume=%s, has_token=%s",
                user_query[:50],
                session_id,
                is_resume,
                bool(token),
            )
            generate_task = asyncio.create_task(
                run_generation(
                    user_query,
                    request_config,
                    progress_callback,
                    access_token=token,
                    base_url=config.bisheng_base_url,
                    session_id=session_id,
                    is_resume=is_resume,
                    original_user_input=original_user_input,
                )
            )

            while True:
                task_done = generate_task.done()

                while not event_queue.empty():
                    try:
                        event = event_queue.get_nowait()
                        if config.is_mysql_configured():
                            try:
                                save_timeline_progress_event(
                                    config, session_id, event.model_dump(mode="json")
                                )
                            except Exception as e:
                                logger.warning("写入会话进度事件失败: %s", e)
                        yield f"data: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                    except asyncio.QueueEmpty:
                        break

                if task_done:
                    try:
                        result = generate_task.result()
                        if result.get("needs_clarification"):
                            # 澄清事件已由 generate_with_progress 发送
                            pass
                        elif result.get("status") == "success":
                            final_event = ProgressEvent(
                                event_type=ProgressEventType.COMPLETE,
                                message="生成完成",
                                data=result,
                                progress=100.0,
                            )
                            if config.is_mysql_configured():
                                try:
                                    save_timeline_progress_event(
                                        config,
                                        session_id,
                                        final_event.model_dump(mode="json"),
                                    )
                                except Exception as e:
                                    logger.warning("写入会话进度事件失败: %s", e)
                            yield f"data: {json.dumps(final_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                    except Exception as e:
                        logger.exception("获取任务结果失败：%s", e)
                    break

                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    if config.is_mysql_configured():
                        try:
                            save_timeline_progress_event(
                                config, session_id, event.model_dump(mode="json")
                            )
                        except Exception as e:
                            logger.warning("写入会话进度事件失败: %s", e)
                    yield f"data: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    logger.warning("SSE 连接被取消")
                    break
                except Exception as e:
                    logger.exception("SSE 事件发送失败：%s", e)
                    break

        except Exception as e:
            logger.error("SSE 生成器错误：%s", e, exc_info=True)
            error_event = ProgressEvent(
                event_type=ProgressEventType.ERROR,
                message=f"生成失败：{str(e)}",
                error=str(e),
                progress=0.0,
            )
            if config.is_mysql_configured():
                try:
                    save_timeline_progress_event(
                        config, session_id, error_event.model_dump(mode="json")
                    )
                except Exception as save_err:
                    logger.warning("写入会话进度事件失败: %s", save_err)
            yield f"data: {json.dumps(error_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"

    response = StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )

    from starlette.background import BackgroundTask

    async def cleanup():
        pass

    response.background = BackgroundTask(cleanup)
    return response


async def run_generation(
    query: str,
    request_config: Optional[dict],
    progress_callback,
    access_token: Optional[str] = None,
    base_url: str = "",
    session_id: Optional[str] = None,
    is_resume: bool = False,
    original_user_input: Optional[str] = None,
) -> dict:
    """
    执行生成任务（支持首轮/续轮）

    Args:
        query: 用户查询（续轮时为用户澄清回复）
        request_config: 请求体中的 config
        progress_callback: 进度回调
        access_token: 毕昇 access_token
        base_url: 毕昇 API base_url
        session_id: 会话 ID
        is_resume: 是否为续轮
        original_user_input: 首轮用户输入（续轮时必传，用于恢复 state）

    Returns:
        生成结果
    """
    logger.info(
        "run_generation 开始，query=%s, session_id=%s, is_resume=%s",
        query[:50],
        session_id,
        is_resume,
    )

    graph_config = {"configurable": {"thread_id": session_id}} if session_id else {}

    try:
        orchestrator = WorkflowOrchestrator(
            config_obj=request_config, progress_callback=progress_callback
        )
        # 知识库在知识库匹配节点内惰性加载，此处不再预加载
        result = await orchestrator.generate_with_progress(
            user_input=query,
            progress_callback=progress_callback,
            session_id=session_id,
            graph_config=graph_config,
            is_resume=is_resume,
            original_user_input=original_user_input,
            bisheng_base_url=base_url,
            access_token=access_token or "",
        )

        # 澄清时不保存/导入
        if result.get("needs_clarification"):
            return result

        if result.get("status") == "success":
            workflow = result.get("workflow")
            if workflow:
                filepath = save_workflow(workflow)
                result["file_path"] = str(filepath)
                logger.info("工作流已保存，path=%s", filepath)

            auto_import = (request_config or {}).get("auto_import", False)
            if auto_import and workflow and progress_callback:
                await progress_callback(
                    ProgressEvent.create_agent_start_event(AgentName.IMPORT)
                )
                start_ts = time.time()
                try:
                    import_result = await do_import_workflow(
                        workflow,
                        base_url,
                        access_token or "",
                        metadata=result.get("metadata"),
                        publish=True,
                    )
                    result["import_result"] = import_result
                    duration_ms = (time.time() - start_ts) * 1000
                    await progress_callback(
                        ProgressEvent.create_agent_complete_event(
                            AgentName.IMPORT,
                            {
                                "flow_id": import_result.get("flow_id"),
                                "version_id": import_result.get("version_id"),
                                "published": import_result.get("published"),
                                "chat_url": import_result.get("chat_url"),
                                "flow_edit_url": import_result.get("flow_edit_url"),
                            },
                            duration_ms,
                        )
                    )
                    logger.info(
                        "工作流已导入毕昇：flow_id=%s", import_result.get("flow_id")
                    )
                except Exception as e:
                    result["import_error"] = str(e)
                    duration_ms = (time.time() - start_ts) * 1000
                    await progress_callback(
                        ProgressEvent.create_agent_error_event(
                            AgentName.IMPORT, str(e), duration_ms
                        )
                    )
                    logger.warning("导入毕昇失败：%s", e)
        return result

    except Exception as e:
        logger.error("生成工作流失败：%s", e, exc_info=True)
        return {"status": "error", "message": f"生成失败：{str(e)}"}


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
