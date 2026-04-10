from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

_api_key: str = ""


def set_api_key(key: str):
    global _api_key
    _api_key = key


def check_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if credentials.credentials != _api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
