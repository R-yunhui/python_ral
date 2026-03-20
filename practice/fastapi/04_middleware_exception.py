"""
FastAPI 学习 - 中间件与异常处理
==============================
本文件涵盖：中间件顺序、请求前后处理、HTTPException、自定义异常与处理器
运行: uvicorn practice.fastapi.04_middleware_exception:app --reload
"""

import time
from typing import Callable

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="中间件与异常示例", docs_url="/docs")


# ============== 一、中间件基础 ==============
# 中间件按添加的「反序」执行：先加的后包在外层（洋葱模型）
# 请求：中间件 A -> B -> 路由；响应：路由 -> B -> A

@app.middleware("http")
async def add_process_time(request: Request, call_next: Callable):
    """每个请求前后计时，并在响应头里返回耗时。"""
    print(f"[Request add_process_time] {request.method} {request.url.path}")
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{duration:.3f}"
    print(f"[Response add_process_time Time] {duration:.3f}s")
    return response


@app.middleware("http")
async def log_request(request: Request, call_next: Callable):
    """先加的中间件后执行：所以请求时先经过 log_request，再 add_process_time，再进路由。"""
    print(f"[Request log_request] {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"[Response log_request] {response.status_code}")
    return response


# ============== 二、类形式中间件（可封装状态） ==============

class CountMiddleware(BaseHTTPMiddleware):
    """用类写中间件，可维护实例状态（这里用类变量简单计数）。"""
    count = 0

    async def dispatch(self, request: Request, call_next: Callable):
        CountMiddleware.count += 1
        request.state.request_count = CountMiddleware.count
        response = await call_next(request)
        print(f"[Response CountMiddleware] {CountMiddleware.count}")
        return response


app.add_middleware(CountMiddleware)


@app.get("/count")
def get_count(request: Request):
    """request.state 可在中间件里挂属性，路由里读取。"""
    return {"request_count": getattr(request.state, "request_count", None)}


# ============== 三、HTTPException ==============

@app.get("/users/{user_id}")
def get_user(user_id: int):
    """主动抛 HTTPException，FastAPI 会转为对应状态码的 JSON 响应。"""
    if user_id < 0:
        raise HTTPException(status_code=400, detail="user_id 必须为正数")
    if user_id > 1000:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"user_id": user_id, "name": "张三"}


@app.get("/error/headers")
def error_with_headers():
    """HTTPException 可带 headers，常用于认证（如 WWW-Authenticate）。"""
    raise HTTPException(
        status_code=401,
        detail="未授权",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ============== 四、自定义异常与全局处理器 ==============

class BusinessError(Exception):
    """业务异常：约定 code 和 message。"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


@app.exception_handler(BusinessError)
async def business_exception_handler(request: Request, exc: BusinessError):
    """捕获 BusinessError，统一返回固定格式的 JSON。"""
    return JSONResponse(
        status_code=200,  # 业务错误有时仍返回 200，用 code 区分
        content={"code": exc.code, "message": exc.message},
    )


@app.get("/order/{order_id}")
def get_order(order_id: str):
    """路由里抛自定义异常，会被上面的 handler 处理。"""
    if order_id == "invalid":
        raise BusinessError(code=10001, message="订单号无效")
    return {"order_id": order_id, "status": "ok"}


# ============== 五、覆盖默认校验错误格式 ==============
# 请求体验证失败时，FastAPI 默认抛 RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """自定义校验错误响应格式，便于前端统一处理。"""
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "请求参数校验失败",
            "details": errors,
        },
    )


@app.post("/validate-demo")
def validate_demo(name: str, age: int):
    """传错类型或缺少参数会触发 RequestValidationError，走上面 handler。"""
    return {"name": name, "age": age}


# ============== 六、依赖里抛异常 ==============

def must_positive(n: int):
    if n <= 0:
        raise HTTPException(status_code=400, detail="n 必须为正数")
    return n


@app.get("/positive")
def use_positive(n: int = Depends(must_positive)):
    """依赖里 raise HTTPException 会直接中断，返回对应响应。"""
    return {"n": n}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
