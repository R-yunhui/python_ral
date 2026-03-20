import asyncio

import threading
from typing import AsyncGenerator

# fastapi 相关
from fastapi import FastAPI, Request
from fastapi.background import BackgroundTasks
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse


app = FastAPI(description="FastAPI demo", docs_url="/docs", version="1.0.0")


class ChatRequest(BaseModel):
    """流式问答请求"""

    query: str = Field(..., description="用户问题", min_length=1)

    chat_id: str = Field(..., description="会话ID")


def _format_sse(data: str, event: str | None = None) -> str:
    """将普通文本打包为 SSE 协议帧。"""
    lines = []
    if event:
        lines.append(f"event: {event}")
    for line in data.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


@app.post("/chat_stream", summary="流式问答")
async def chat_stream(chat_request: ChatRequest, request: Request):

    async def event_generator() -> AsyncGenerator[str, None]:
        yield _format_sse(f"用户问题: {chat_request.query}", event="start")
        i = 0
        while i <= 10:
            if await request.is_disconnected():
                print("客户端断开连接")
                break

            yield _format_sse(f"开始执行任务 {i} ...", event="progress")
            i += 1

            # 模拟耗时 1s
            await asyncio.sleep(1)

            yield _format_sse(f"任务 {i} 执行完成！", event="progress")

        yield _format_sse("所有任务执行完成！", event="done")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(
        event_generator(), headers=headers, media_type="text/event-stream"
    )


@app.post("/chat/end", summary="结束会话")
async def chat_end(chat_request: ChatRequest, background_tasks: BackgroundTasks):
    """
    在响应已经发给客户端之后执行一段异步任务
    """
    print(f"会话ID: {chat_request.chat_id} 结束")
    background_tasks.add_task(end_chat, chat_request)
    return {"message": "会话结束"}


@app.get("/test/io")
async def test_io() -> dict[str, str]:
    print(f"{threading.current_thread().name}")
    import time

    """
    模拟一个耗时的 io 操作
    """
    time.sleep(20)
    return {"message": "io 操作完成"}


@app.get("/ahello")
async def hello() -> dict[str, str]:
    print(f"{threading.current_thread().name}")
    return {"message": "hello"}


@app.get("/hello")
def hello() -> dict[str, str]:
    print(f"{threading.current_thread().name}")
    return {"message": "hello"}


async def end_chat(chat_request: ChatRequest):
    """结束会话"""
    print(f"会话ID: {chat_request.chat_id} 结束")
    await asyncio.sleep(10)
    return {"message": "会话结束"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8010)
