"""毕昇工作流生成器 - FastAPI 接口"""

import logging
from typing import Optional, AsyncGenerator
import json
import time
from pathlib import Path
from asyncio import Queue

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config.config import config
from core.graph import WorkflowOrchestrator
from main import save_workflow
from models.progress import ProgressEvent, StreamResponse

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="毕昇工作流生成器 API",
    description="提供工作流生成、查看和下载的 API 接口",
    version="0.2.0"
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
                status_code=404
            )
    except Exception as e:
        logger.error(f"读取前端页面失败：{e}")
        raise HTTPException(status_code=500, detail=f"读取页面失败：{str(e)}")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_workflow(request: GenerateRequest):
    """
    生成工作流
    
    Args:
        request: 生成请求，包含用户查询
    
    Returns:
        生成的工作流
    """
    logger.info(f"收到生成请求：{request.query[:50]}...")
    
    try:
        # 创建编排器
        orchestrator = WorkflowOrchestrator(request.config)
        
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
                error=result.get("message")
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
            workflows.append({
                "filename": file.name,
                "filepath": str(file),
                "created_at": file.stat().st_mtime,
                "size": file.stat().st_size
            })
        
        return workflows
    except Exception as e:
        logger.error(f"获取工作流列表失败：{e}")
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
        
        return {
            "filename": filename,
            "workflow": workflow
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取工作流失败：{e}")
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
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载工作流失败：{e}")
        raise HTTPException(status_code=500, detail=f"下载失败：{str(e)}")


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": "0.2.0"
    }


@app.post("/api/generate/stream")
async def generate_workflow_stream(request: GenerateRequest):
    """
    生成工作流（流式 SSE 版本）
    
    Args:
        request: 生成请求，包含用户查询
    
    Returns:
        SSE 事件流，实时推送进度
    """
    logger.info(f"收到流式生成请求：{request.query[:50]}...")
    
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
            # 启动生成任务
            generate_task = asyncio.create_task(
                run_generation(request.query, request.config, progress_callback)
            )
            
            # 持续从队列读取事件
            while True:
                try:
                    # 等待事件或任务完成
                    get_task = asyncio.create_task(event_queue.get())
                    done, pending = await asyncio.wait(
                        [get_task, generate_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # 如果生成任务完成
                    if generate_task in done:
                        result = generate_task.result()
                        # 发送最终结果事件
                        final_event = ProgressEvent(
                            event_type="final_result",
                            message="生成完成",
                            data=result
                        )
                        yield f"event: final_result\ndata: {json.dumps(final_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                        break
                    
                    # 取消 pending 任务
                    for task in pending:
                        task.cancel()
                    
                    # 获取并发送事件
                    event = get_task.result()
                    yield f"event: progress\ndata: {json.dumps(event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                    
                except asyncio.CancelledError:
                    logger.warning("SSE 连接被取消")
                    break
                except Exception as e:
                    logger.error(f"SSE 事件发送失败：{e}")
                    error_event = ProgressEvent(
                        event_type="error",
                        message=f"推送失败：{str(e)}",
                        error=str(e)
                    )
                    yield f"event: error\ndata: {json.dumps(error_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
                    break
        
        except Exception as e:
            logger.error(f"SSE 生成器错误：{e}", exc_info=True)
            error_event = ProgressEvent(
                event_type="error",
                message=f"生成失败：{str(e)}",
                error=str(e)
            )
            yield f"event: error\ndata: {json.dumps(error_event.model_dump(mode='json'), ensure_ascii=False)}\n\n"
    
    # 返回 SSE 响应
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx: 禁用缓冲
        }
    )


async def run_generation(
    query: str,
    config: Optional[dict],
    progress_callback
) -> dict:
    """
    执行生成任务
    
    Args:
        query: 用户查询
        config: 配置
        progress_callback: 进度回调
    
    Returns:
        生成结果
    """
    try:
        # 创建编排器
        orchestrator = WorkflowOrchestrator(
            config_obj=config,
            progress_callback=progress_callback
        )
        
        # 生成工作流
        result = await orchestrator.generate_with_progress(
            user_input=query,
            progress_callback=progress_callback
        )
        
        if result.get("status") == "success":
            # 保存工作流
            workflow = result.get("workflow")
            if workflow:
                filepath = save_workflow(workflow)
                result["file_path"] = str(filepath)
                logger.info(f"工作流已保存：{filepath}")
        
        return result
    
    except Exception as e:
        logger.error(f"生成工作流失败：{e}", exc_info=True)
        return {
            "status": "error",
            "message": f"生成失败：{str(e)}"
        }


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
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=config.log_level.lower()
    )


if __name__ == "__main__":
    main()
