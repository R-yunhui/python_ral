"""
FastAPI 学习 - 安全认证（OAuth2 / JWT 入门）
===========================================
本文件涵盖：OAuth2 密码流、JWT 创建与校验、依赖里获取当前用户、Bearer Token
运行: uvicorn practice.fastapi.06_security_oauth2:app --reload
依赖: pip install python-jose[cryptography] passlib[bcrypt]
"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

app = FastAPI(title="安全认证示例", docs_url="/docs")

# 配置（生产环境应从环境变量读取）
SECRET_KEY = "123456"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 密码流：tokenUrl 指向我们提供的登录接口，/docs 里会多出 Authorize 按钮
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# 可选：仅 Bearer 不限定 OAuth2 流
http_bearer = HTTPBearer()


# ============== 一、模拟用户库与密码校验 ==============

class User(BaseModel):
    """内部用，含密码哈希，不要直接作为响应返回。"""
    username: str
    hashed_password: str
    disabled: bool = False


class UserOut(BaseModel):
    """返回给前端的用户信息，不含密码。"""
    username: str
    disabled: bool = False


# 模拟数据库：用户名 -> 用户信息（密码已哈希）
fake_users_db: dict[str, User] = {
    "admin": User(
        username="admin",
        hashed_password=pwd_context.hash("admin123"),
    ),
    "user": User(
        username="user",
        hashed_password=pwd_context.hash("user123"),
    ),
}


def verify_password(plain: str, hashed: str) -> bool:
    """明文密码与哈希比对。"""
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    """注册时用：明文转哈希再存库。"""
    return pwd_context.hash(password)


def get_user_from_db(username: str) -> User | None:
    return fake_users_db.get(username)


def authenticate_user(username: str, password: str) -> User | None:
    """校验用户名密码，成功返回 User。"""
    user = get_user_from_db(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


# ============== 二、JWT 创建与解析 ==============

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 JWT：payload 里放 sub（通常为 username），过期时间等。"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解析 JWT，失败返回 None。"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ============== 三、登录接口（OAuth2 密码流） ==============
# 前端/客户端用表单提交 username + password，换 access_token

@app.post("/token", summary="登录获取 token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2PasswordRequestForm 会解析 form 里的 username、password（不是 JSON）。
    成功返回 access_token 和 token_type，符合 OAuth2 规范。
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ============== 四、依赖：从 token 取当前用户 ==============

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    oauth2_scheme 会从请求头 Authorization: Bearer <token> 里取 token；
    未带或格式错误会直接 401。这里再校验 JWT 并查用户。
    """
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的 token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str | None = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="token 中缺少 sub")
    user = get_user_from_db(username)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.disabled:
        raise HTTPException(status_code=400, detail="用户已禁用")
    return user


# 类型别名，方便路由使用
CurrentUser = Annotated[User, Depends(get_current_user)]


@app.get("/users/me", summary="获取当前用户", response_model=UserOut)
def read_me(current_user: CurrentUser):
    """需要在请求头带 Authorization: Bearer <access_token>。response_model 避免把 hashed_password 返回。"""
    return current_user


# ============== 五、可选 Token（仅 Bearer，不强制登录） ==============

async def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
) -> User | None:
    """未带 token 时返回 None，带了则校验并返回 User。"""
    if creds is None:
        return None
    payload = decode_token(creds.credentials)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None
    return get_user_from_db(username)


@app.get("/optional-auth")
def optional_auth(user: User | None = Depends(get_current_user_optional)):
    """有 token 则返回用户信息，没有则返回 guest。"""
    if user:
        return {"user": user.username, "auth": True}
    return {"user": "guest", "auth": False}


# ============== 六、权限：仅管理员 ==============

def require_admin(current_user: CurrentUser) -> User:
    """依赖：当前用户必须是 admin。"""
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@app.get("/admin-only", summary="仅管理员")
def admin_only(admin: User = Depends(require_admin)):
    return {"message": f"欢迎管理员 {admin.username}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
