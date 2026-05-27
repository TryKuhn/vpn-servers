from __future__ import annotations

import json

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from manager.config import Settings, get_settings
from manager.db import get_session
from manager.repository import get_device_by_token, record_subscription_request
from manager.subscriptions import (
    build_hysteria_subscription,
    build_naive_subscription,
    build_v2ray_subscription,
    build_xray_xhttp_subscription,
    device_is_allowed,
)

app = FastAPI(title="trykuhn-vpn-manager", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _load_device_or_404(
    token: str,
    request: Request,
    session: AsyncSession,
):
    device = await get_device_by_token(session, token)

    if device is None or not device_is_allowed(device):
        raise HTTPException(status_code=404, detail="subscription not found")

    await record_subscription_request(
        session,
        device,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()

    return device


def _json_response(payload: dict, device, settings: Settings, profile: str) -> Response:
    body = json.dumps(payload, ensure_ascii=False, indent=2)

    filename_user = device.user.name.replace(" ", "-")
    filename_device = device.name.replace(" ", "-")

    headers = {
        "profile-title": settings.subscription_profile_title,
        "subscription-userinfo": "upload=0; download=0; total=0; expire=0",
        "content-disposition": (
            f'attachment; filename="{filename_user}-{filename_device}-{profile}.json"'
        ),
    }

    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers=headers,
    )


@app.get("/sub/{token}")
async def subscription_default(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """
    Legacy/default endpoint.

    Сейчас intentionally NaiveProxy-only, потому что Hiddify/sing-box
    не поддерживает XHTTP transport и нестабильно ведёт себя со смешанным профилем.
    """
    device = await _load_device_or_404(token, request, session)
    payload = build_naive_subscription(device, settings)
    return _json_response(payload, device, settings, "naive")


@app.get("/sub/naive/{token}")
async def subscription_naive(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    device = await _load_device_or_404(token, request, session)
    payload = build_naive_subscription(device, settings)
    return _json_response(payload, device, settings, "naive")


@app.get("/sub/hysteria/{token}")
async def subscription_hysteria(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    device = await _load_device_or_404(token, request, session)
    payload = build_hysteria_subscription(device, settings)
    return _json_response(payload, device, settings, "hysteria2")


@app.get("/sub/xray/{token}")
async def subscription_xray(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    device = await _load_device_or_404(token, request, session)
    payload = build_xray_xhttp_subscription(device, settings)
    return _json_response(payload, device, settings, "xray-xhttp")


@app.get("/sub/v2ray/{token}")
async def subscription_v2ray(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """
    Стандартный subscription формат для V2RayTun, NekoBox, Hiddify и аналогов.
    Возвращает base64-encoded список VLESS URI (XHTTP+Reality).
    """
    device = await _load_device_or_404(token, request, session)
    content = build_v2ray_subscription(device, settings)

    filename_user = device.user.name.replace(" ", "-")
    filename_device = device.name.replace(" ", "-")

    headers = {
        "profile-title": settings.subscription_profile_title,
        "subscription-userinfo": "upload=0; download=0; total=0; expire=0",
        "content-disposition": (
            f'attachment; filename="{filename_user}-{filename_device}-v2ray.txt"'
        ),
    }

    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers=headers,
    )