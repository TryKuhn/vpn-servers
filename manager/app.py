from __future__ import annotations

import json
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from manager.config import get_settings, Settings
from manager.db import get_session
from manager.repository import get_device_by_token, record_subscription_request
from manager.subscriptions import build_singbox_subscription, device_is_allowed

app = FastAPI(title="trykuhn-vpn-manager", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sub/{token}")
async def subscription(token: str, request: Request, session: AsyncSession = Depends(get_session), settings: Settings = Depends(get_settings)) -> Response:
    device = await get_device_by_token(session, token)
    if device is None or not device_is_allowed(device):
        raise HTTPException(status_code=404, detail="subscription not found")
    await record_subscription_request(session, device, ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    await session.commit()
    payload = build_singbox_subscription(device, settings)
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    headers = {"profile-title": settings.subscription_profile_title, "subscription-userinfo": "upload=0; download=0; total=0; expire=0", "content-disposition": f'attachment; filename="{device.user.name}-{device.name}.json"'}
    return Response(content=body, media_type="application/json; charset=utf-8", headers=headers)
