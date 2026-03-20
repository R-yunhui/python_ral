"""
FastAPI 学习 - 请求与响应
========================
本文件涵盖：路径参数、查询参数、请求体、响应模型、状态码、Cookie/Header、文件上传
运行: uvicorn practice.fastapi.02_request_response:app --reload
"""

from enum import Enum
from typing import Any

from fastapi import FastAPI, Query, Path, Body, Cookie, Header, status, UploadFile, File
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

app = FastAPI(title="请求与响应示例", docs_url="/docs")


# ============== 一、路径参数 ==============
# 路径参数写在 URL 路径中，如 /items/123 里的 123

@app.get("/items/{item_id}", summary="路径参数")
def get_item(item_id: int):
    """item_id 会从 URL 中解析并自动转为 int，类型错误时自动 422。"""
    return {"item_id": item_id}


# 路径顺序：更具体的路由要写在更通用的前面
@app.get("/users/me", summary="固定路径优先")
def read_user_me():
    """'/users/me' 必须在 '/users/{user_id}' 之前，否则 'me' 会被当作 user_id。"""
    return {"user": "current user"}


@app.get("/users/{user_id}")
def read_user(user_id: str):
    return {"user_id": user_id}


# 枚举做路径参数，只接受枚举值
class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


@app.get("/sort/{order}")
def sort_items(order: SortOrder):
    """order 只能是 'asc' 或 'desc'，否则 422。"""
    return {"order": order.value}


# ============== 二、查询参数 ==============
# 问号后的参数，如 ?skip=0&limit=10

@app.get("/items/", summary="可选与必选查询参数")
def list_items(
    skip: int = 0,           # 可选，默认 0
    limit: int = Query(10, ge=1, le=100),  # 可选，默认 10，且 1<=limit<=100
    q: str | None = None,   # 可选，None 表示可以不传
):
    """Query() 可写默认值、校验、描述，用于 OpenAPI 文档。"""
    return {"skip": skip, "limit": limit, "q": q}


@app.get("/search/", summary="多值查询参数")
def search(tags: list[str] = Query(..., description="标签列表")):
    """?tags=py&tags=web 会得到 tags=['py','web']。"""
    return {"tags": tags}


# ============== 三、请求体（Pydantic） ==============

class Item(BaseModel):
    """请求体模型：JSON 自动反序列化并校验。"""
    name: str = Field(..., min_length=1, description="商品名")
    price: float = Field(gt=0, description="价格")
    is_offer: bool = False
    tags: list[str] = Field(default_factory=list, description="标签")


@app.post("/items/", summary="请求体", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    """Body 默认从请求体 JSON 读取，校验失败自动 422。"""
    return {"name": item.name, "price": item.price, "is_offer": item.is_offer}


# 路径 + 查询 + 请求体 同时使用
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item, q: str | None = None):
    """路径参数、查询参数、请求体可以一起用。"""
    return {"item_id": item_id, **item.model_dump(), "q": q}


# Body() 单字段、嵌入 key
@app.post("/embed")
def embed_body(item: Item = Body(..., embed=True)):
    """embed=True 时期望 JSON 形如 {"item": {"name":"x","price":1}}。"""
    return item


# ============== 四、响应 ==============

@app.get("/resp/json", response_model=dict[str, Any])
def resp_json():
    """直接返回 dict，FastAPI 会序列化为 JSON。"""
    return {"key": "value"}


class UserOut(BaseModel):
    """响应模型：只返回这里声明的字段，且会做序列化校验。"""
    name: str
    age: int


@app.get("/resp/model", response_model=UserOut)
def resp_model():
    """response_model 会过滤并校验返回结构。"""
    return {"name": "张三", "age": 18, "internal_id": 999}  # internal_id 不会出现在响应里


@app.get("/resp/status", status_code=status.HTTP_201_CREATED)
def resp_status():
    """status_code 指定成功时的 HTTP 状态码。"""
    return {"created": True}


@app.get("/resp/custom", response_class=PlainTextResponse)
def resp_plain():
    """response_class 可改为纯文本、HTML 等。"""
    return "plain text"


@app.get("/resp/direct")
def resp_direct():
    """需要完全自定义状态码和头部时用 JSONResponse。"""
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"msg": "accepted"},
        headers={"X-Custom": "value"},
    )


# ============== 五、Cookie 与 Header ==============

@app.get("/cookie")
def read_cookie(session_id: str | None = Cookie(None)):
    """Cookie() 从请求的 Cookie 里取同名变量。"""
    return {"session_id": session_id}


@app.get("/header")
def read_header(
    user_agent: str | None = Header(None),
    x_request_id: str | None = Header(None, alias="X-Request-ID"),
):
    """Header() 从请求头取值；alias 可映射带连字符的 header 名。"""
    return {"user_agent": user_agent, "x_request_id": x_request_id}


# ============== 六、文件上传 ==============

@app.post("/upload", summary="单文件上传")
async def upload_file(file: UploadFile = File(...)):
    """UploadFile 支持大文件流式读取，可读 filename、content_type。"""
    content = await file.read()
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
    }


@app.post("/upload-multi", summary="多文件上传")
async def upload_multi(files: list[UploadFile] = File(...)):
    """多文件：list[UploadFile]。"""
    return [{"filename": f.filename, "size": len(await f.read())} for f in files]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
