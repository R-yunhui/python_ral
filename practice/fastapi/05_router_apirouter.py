"""
FastAPI 学习 - 路由与 APIRouter
==============================
本文件涵盖：APIRouter、前缀与标签、include_router、路由依赖、多应用挂载
运行: uvicorn practice.fastapi.05_router_apirouter:app --reload
"""

from fastapi import APIRouter, Depends, FastAPI

app = FastAPI(title="APIRouter 示例", docs_url="/docs")


# ============== 一、APIRouter 基础 ==============
# 把一组路由拆到 router，再 include_router 挂到 app，便于分模块开发

# 用户相关路由
users_router = APIRouter(
    prefix="/users",       # 所有路由前都会加 /users
    tags=["用户"],         # 在 /docs 里归到「用户」分组
    responses={404: {"description": "用户不存在"}},
)


@users_router.get("/")
def list_users():
    """实际路径: GET /users/"""
    return [{"id": 1, "name": "张三"}, {"id": 2, "name": "李四"}]


@users_router.get("/{user_id}")
def get_user(user_id: int):
    """实际路径: GET /users/{user_id}"""
    return {"id": user_id, "name": "张三"}


# 商品相关路由
items_router = APIRouter(
    prefix="/items",
    tags=["商品"],
)


@items_router.get("/")
def list_items():
    return [{"id": 1, "name": "书"}, {"id": 2, "name": "笔"}]


@items_router.get("/{item_id}")
def get_item(item_id: int):
    return {"id": item_id, "name": "书"}


# 挂载到主应用（同一 router 可多次挂载不同 prefix）
app.include_router(users_router)           # /users/、/users/{user_id}
app.include_router(items_router)
app.include_router(users_router, prefix="/v1")  # 再挂一份：/v1/users/、/v1/users/{user_id}


# ============== 二、路由级依赖 ==============
# 在 router 上加 dependencies，该 router 下所有路由都会先执行这些依赖

def get_current_user():
    """模拟从 token 取当前用户（这里写死）。"""
    return {"user_id": 1, "username": "admin"}


# 需要登录的 router
admin_router = APIRouter(
    prefix="/admin",
    tags=["管理"],
    dependencies=[Depends(get_current_user)],  # 所有 /admin 下路由都要过这个依赖
)


@admin_router.get("/")
def admin_index():
    """GET /admin/ 会先执行 get_current_user，失败则不会进这里。"""
    return {"message": "管理后台"}


@admin_router.get("/stats")
def admin_stats():
    return {"users": 100, "orders": 200}


app.include_router(admin_router)


# ============== 三、前缀叠加 ==============
# 上面已用 include_router(users_router, prefix="/v1")，最终路径为 /v1/users/、/v1/users/{user_id}
# 即：app 的 prefix（无） + include_router 的 prefix（/v1） + router 自己的 prefix（/users）

# ============== 四、按模块拆分到多文件（示意） ==============
# 实际项目里常把 router 写在 routers/users.py、routers/items.py，
# 在 main.py 里：
#   from routers.users import users_router
#   from routers.items import items_router
#   app.include_router(users_router)
#   app.include_router(items_router)


# ============== 五、根路由留在 app ==============

@app.get("/")
def root():
    return {"message": "FastAPI APIRouter 示例", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
