from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import csv

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from manager.models import Device, User
from manager.utils import new_password, new_token, new_uuid, slugify


def _active_user_device_stmt() -> Select[tuple[Device]]:
    return (
        select(Device)
        .options(selectinload(Device.user))
        .join(User)
        .where(User.enabled.is_(True), Device.enabled.is_(True), Device.revoked_at.is_(None))
    )


async def get_user_by_name(session: AsyncSession, name: str) -> User | None:
    result = await session.execute(select(User).options(selectinload(User.devices)).where(User.name == name))
    return result.scalar_one_or_none()


async def get_device_by_token(session: AsyncSession, token: str) -> Device | None:
    result = await session.execute(select(Device).options(selectinload(Device.user)).where(Device.subscription_token == token))
    return result.scalar_one_or_none()


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).options(selectinload(User.devices)).order_by(User.name.asc()))
    return list(result.scalars().unique())


async def list_active_devices(session: AsyncSession) -> list[Device]:
    result = await session.execute(_active_user_device_stmt().order_by(Device.id.asc()))
    devices = list(result.scalars().unique())
    now = datetime.now(timezone.utc)
    return [d for d in devices if d.user.expires_at is None or d.user.expires_at > now]


async def create_user_with_default_device(
    session: AsyncSession,
    *,
    name: str,
    device_name: str | None = None,
    os_name: str | None = None,
    subscription_token: str | None = None,
    vless_uuid: str | None = None,
    note: str | None = None,
) -> tuple[User, Device, bool]:
    existing = await get_user_by_name(session, name)
    if existing is not None:
        default_device = existing.devices[0] if existing.devices else None
        if default_device is None:
            default_device = _make_device(existing, device_name or name, os_name, subscription_token, vless_uuid)
            session.add(default_device)
            await session.flush()
        return existing, default_device, False

    user = User(name=name, login=name, enabled=True, note=note)
    session.add(user)
    await session.flush()

    device = _make_device(user, device_name or name, os_name, subscription_token, vless_uuid)
    session.add(device)
    await session.flush()
    return user, device, True


def _make_device(user: User, device_name: str, os_name: str | None, subscription_token: str | None, vless_uuid: str | None) -> Device:
    base = slugify(f"{user.name}_{device_name}")
    return Device(
        user_id=user.id,
        name=device_name,
        os=os_name,
        enabled=True,
        subscription_token=subscription_token or new_token(),
        vless_uuid=vless_uuid or new_uuid(),
        hysteria_username=base[:120],
        hysteria_password=new_password(),
        naive_username=base[:120],
        naive_password=new_password(),
    )


async def add_device_to_user(
    session: AsyncSession,
    *,
    user_name: str,
    device_name: str,
    os_name: str | None = None,
) -> tuple[Device, bool] | tuple[None, None]:
    user = await get_user_by_name(session, user_name)
    if user is None:
        return None, None
    existing = next((d for d in user.devices if d.name.lower() == device_name.lower()), None)
    if existing is not None:
        return existing, False
    device = _make_device(user, device_name, os_name, None, None)
    session.add(device)
    await session.flush()
    return device, True


async def remove_user(session: AsyncSession, name: str) -> bool:
    user = await get_user_by_name(session, name)
    if user is None:
        return False
    await session.delete(user)
    await session.flush()
    return True


async def set_user_enabled(session: AsyncSession, name: str, enabled: bool) -> bool:
    user = await get_user_by_name(session, name)
    if user is None:
        return False
    user.enabled = enabled
    await session.flush()
    return True


async def rotate_user_default_device_token(session: AsyncSession, name: str) -> Device | None:
    user = await get_user_by_name(session, name)
    if user is None or not user.devices:
        return None
    device = user.devices[0]
    device.subscription_token = new_token()
    await session.flush()
    return device


async def import_legacy_csv(session: AsyncSession, file_path: str | Path) -> tuple[int, int]:
    created = 0
    skipped = 0
    with Path(file_path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"name", "subscription_token", "vless_uuid"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError("CSV must contain columns: name, subscription_token, vless_uuid")
        for row in reader:
            name = (row.get("name") or "").strip()
            token = (row.get("subscription_token") or "").strip()
            vless_uuid = (row.get("vless_uuid") or "").strip()
            note = (row.get("note") or "legacy import").strip()
            if not name or not token or not vless_uuid:
                skipped += 1
                continue
            _, _, was_created = await create_user_with_default_device(
                session,
                name=name,
                device_name=row.get("device_name") or name,
                os_name=row.get("os") or None,
                subscription_token=token,
                vless_uuid=vless_uuid,
                note=note,
            )
            if was_created:
                created += 1
            else:
                skipped += 1
    await session.flush()
    return created, skipped


async def record_subscription_request(session: AsyncSession, device: Device, *, ip: str | None, user_agent: str | None) -> None:
    device.last_subscription_request_at = datetime.now(timezone.utc)
    device.last_subscription_ip = ip
    device.last_subscription_user_agent = user_agent[:512] if user_agent else None
    await session.flush()
