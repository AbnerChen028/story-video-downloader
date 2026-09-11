"""简单密钥认证"""
import hashlib
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse
from backend.config import settings

auth_router = APIRouter(tags=["auth"])

# 密钥的 SHA256（避免明文比较）
_KEY_HASH = hashlib.sha256(settings.AUTH_KEY.encode()).hexdigest()


def verify_key(key: str) -> bool:
    return hashlib.sha256(key.encode()).hexdigest() == _KEY_HASH


@auth_router.post("/api/auth/verify")
async def verify(
    key: str = Body(..., embed=True),
):
    """验证密钥，设置永久 Cookie"""
    if not verify_key(key):
        raise HTTPException(status_code=401, detail="密钥错误")

    resp = JSONResponse({"status": "ok"})
    resp.set_cookie(
        key="auth_key", value=key,
        httponly=True, samesite="lax",
        # 设置为 2038 年过期（"永久"）
        max_age=10 * 365 * 86400,
        path="/",
    )
    return resp


@auth_router.get("/api/auth/check")
async def check(request: Request):
    """检查 Cookie 中的密钥是否有效"""
    key = request.cookies.get("auth_key", "")
    if key and verify_key(key):
        return {"status": "ok"}
    raise HTTPException(status_code=401, detail="未授权")


@auth_router.post("/api/auth/logout")
async def logout():
    """清除密钥 Cookie"""
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie("auth_key", path="/")
    return resp
