# FastAPI 学习示例

按文件顺序学习，每个文件聚焦一类知识点，注释完整。

| 文件 | 内容 | 建议端口 |
|------|------|----------|
| `01_fastapi_demo.py` | 入门：流式 SSE、BackgroundTasks、Pydantic 请求体 | 8000 |
| `02_request_response.py` | 路径/查询/请求体、响应模型、状态码、Cookie/Header、文件上传 | 8001 |
| `03_validation_dependency.py` | Path/Query 校验、依赖注入、子依赖、Annotated 复用 | 8002 |
| `04_middleware_exception.py` | 中间件、HTTPException、自定义异常与处理器 | 8003 |
| `05_router_apirouter.py` | APIRouter、前缀与标签、include_router、路由级依赖 | 8004 |
| `06_security_oauth2.py` | OAuth2 密码流、JWT、Bearer、当前用户与可选认证 | 8005 |

## 运行方式

在项目根目录（`ral`）下：

```bash
# 激活虚拟环境后
uvicorn practice.fastapi.01_fastapi_demo:app --reload --port 8000
uvicorn practice.fastapi.02_request_response:app --reload --port 8001
# ...
```

或进入 `practice/fastapi` 后：

```bash
python 01_fastapi_demo.py   # 默认 8000
python 02_request_response.py  # 默认 8001
```

## 依赖

- `fastapi`、`uvicorn`
- `06_security_oauth2.py` 额外需要：`python-jose[cryptography]`、`passlib[bcrypt]`

```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

## 推荐学习顺序

1. 先跑通 `01`，看流式与后台任务。
2. 学 `02` 掌握请求响应各种写法。
3. 学 `03` 理解依赖注入（FastAPI 核心之一）。
4. 学 `04`、`05` 做中间件、异常和路由拆分。
5. 最后学 `06` 做登录与 JWT 认证。

每个示例都提供 `/docs`，可用 Swagger UI 直接调试接口。
