"""
FastAPI 学习 - 数据校验与依赖注入
================================
本文件涵盖：Path/Query/Body 校验、依赖注入、子依赖、依赖缓存、类作为依赖
运行: uvicorn practice.fastapi.03_validation_dependency:app --reload
"""

from typing import Annotated

from fastapi import FastAPI, Depends, Query, Path, Body
from pydantic import BaseModel, Field

app = FastAPI(title="校验与依赖注入示例", docs_url="/docs")


# ============== 一、Path / Query / Body 校验 ==============
# 用 Annotated 集中写校验，接口签名更简洁

# 类型别名：带校验的注解，可复用
ItemIdPath = Annotated[int, Path(ge=1, description="商品 ID")]
PageQuery = Annotated[int, Query(ge=1, le=1000, description="页码")]
PageSizeQuery = Annotated[int, Query(ge=1, le=100, alias="page_size")]


@app.get("/items/{item_id}", summary="Path 校验")
def get_item(item_id: ItemIdPath):
    """Path(ge=1) 保证 item_id>=1，否则自动 422 并返回错误详情。"""
    return {"item_id": item_id}


@app.get("/list/", summary="Query 校验")
def list_items(page: PageQuery = 1, page_size: PageSizeQuery = 10):
    """Query 的 ge/le 限制范围；alias 指定 URL 参数名（如 page_size）。"""
    return {"page": page, "page_size": page_size}


class ItemBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    price: float = Field(gt=0, le=99999)


@app.post("/items/")
def create_item(item: Annotated[ItemBody, Body(..., examples=[{"name": "书", "price": 29.9}])]):
    """Body 里可写 examples，会在 /docs 里展示。"""
    return item


# ============== 二、依赖注入基础 ==============
# Depends() 声明依赖，FastAPI 在请求时解析并注入

# 1. 普通函数依赖
# 可以把 Depends 理解为把一些通用的参数逻辑抽离成一个公共函数（如 common_query），
# 然后通过 Depends 注入到不同的接口中，实现依赖复用。
def common_query(q: str | None = Query(None), skip: int = 0, limit: int = 10):
    """返回一个 dict，注入到路由时可用。"""
    return {"q": q, "skip": skip, "limit": limit}


@app.get("/search/")
def search(params: dict = Depends(common_query)):
    """
    params 由 common_query 的返回值注入。
    这个 Depends 可以理解为把参数获取与校验逻辑抽离为公共依赖，然后在路由里直接引入和复用。
    """
    return params


# 2. 依赖返回字典，路由里用其中字段
@app.get("/search2/")
def search2(params: dict = Depends(common_query)):
    """依赖返回整个 params，按需取 q、skip、limit。"""
    return {"skip": params["skip"], "limit": params["limit"], "q": params["q"]}


def get_skip_limit(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return {"skip": skip, "limit": limit}


@app.get("/search3/")
def search3(skip_limit: dict = Depends(get_skip_limit)):
    """正确：用单独依赖返回 skip/limit。"""
    return skip_limit


# 3. 类作为依赖（可读性更好）
class Pagination:
    def __init__(
        self,
        skip: int = Query(0, ge=0, alias="offset"),
        limit: int = Query(10, ge=1, le=100),
    ):
        self.skip = skip
        self.limit = limit


@app.get("/items-paged/")
def items_paged(pagination: Pagination = Depends()):
    """Depends() 无参数时，按类型 Pagination 注入；Pagination 的 __init__ 参数即依赖项。"""
    return {"skip": pagination.skip, "limit": pagination.limit}


# ============== 三、子依赖 ==============
# 依赖可以依赖别的依赖

def get_db():
    """模拟 DB 连接（实际可返回 Session）。"""
    return "db_connection"


def get_user(db: str = Depends(get_db)):
    """依赖 get_db，再根据 db 查用户。"""
    # 这里简化：实际会查数据库
    return {"user_id": "u1", "db": db}


@app.get("/me/")
def read_me(user: dict = Depends(get_user)):
    """read_me 依赖 get_user，get_user 依赖 get_db；三者都会执行。"""
    return user


# ============== 四、同一依赖多次使用与缓存 ==============
# 同一请求内，同一依赖只执行一次，结果被复用

def get_counter():
    """每次调用理论上会 +1（这里用简单计数器模拟）。"""
    get_counter.called = getattr(get_counter, "called", 0) + 1
    return get_counter.called


@app.get("/counter-a/")
def counter_a(c: int = Depends(get_counter)):
    return {"counter": c}


@app.get("/counter-b/")
def counter_b(c: int = Depends(get_counter)):
    return {"counter": c}


@app.get("/counter-both/")
def counter_both(
    c1: int = Depends(get_counter),
    c2: int = Depends(get_counter),
):
    """同一请求里 get_counter 只执行一次，c1 和 c2 相同。"""
    return {"c1": c1, "c2": c2}


# ============== 五、全局依赖 ==============
# 在 app 或 router 上挂 dependency_overrides 可替换依赖（常用于测试）
# 这里演示在 FastAPI() 里加 dependencies

def verify_token(x_token: str = Query(..., alias="X-Token")):
    if x_token != "secret":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid token")
    return x_token


# 若希望所有路由都校验 token，可：app = FastAPI(dependencies=[Depends(verify_token)])
# 这里不全局加，只在需要的地方用
@app.get("/protected/")
def protected(token: str = Depends(verify_token)):
    """此路由依赖 verify_token，请求里必须带 X-Token=secret。"""
    return {"token": token}


# ============== 六、Annotated 简化 Depends 写法 ==============
# 把 Depends 写进类型别名，路由里不用重复写 Depends(...)

CommonQueryDep = Annotated[dict, Depends(common_query)]


@app.get("/search-clean/")
def search_clean(params: CommonQueryDep):
    """params 自动注入 common_query 的返回值，写法更简洁。"""
    return params


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
