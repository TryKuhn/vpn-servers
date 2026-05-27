from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
import typer
from manager.config import get_settings
from manager.db import AsyncSessionLocal
from manager.renderer import render_all
from manager.repository import create_user_with_default_device, get_user_by_name, import_legacy_csv, list_active_devices, list_users, remove_user, rotate_user_default_device_token, set_user_enabled

app = typer.Typer(no_args_is_help=True)

def run(coro):
    return asyncio.run(coro)

@app.command("add-user")
def add_user(name: str = typer.Argument(...), device_name: Optional[str] = typer.Option(None, "--device"), os_name: Optional[str] = typer.Option(None, "--os"), token: Optional[str] = typer.Option(None, "--token"), uuid: Optional[str] = typer.Option(None, "--uuid"), note: Optional[str] = typer.Option(None, "--note")):
    async def _inner():
        async with AsyncSessionLocal() as session:
            user, device, created = await create_user_with_default_device(session, name=name, device_name=device_name, os_name=os_name, subscription_token=token, vless_uuid=uuid, note=note)
            await session.commit()
            typer.echo(f"User {'created' if created else 'exists'}: {user.name}")
            typer.echo(f"Device: {device.name}")
            typer.echo(f"Subscription URL: {get_settings().subscription_base_url}/{device.subscription_token}")
    run(_inner())

@app.command("list-users")
def cli_list_users():
    async def _inner():
        async with AsyncSessionLocal() as session:
            users = await list_users(session)
            if not users:
                typer.echo("No users")
                return
            for user in users:
                typer.echo(f"{user.name}\t{'enabled' if user.enabled else 'disabled'}\tdevices={len(user.devices)}\tlimit={user.device_limit}")
    run(_inner())

@app.command("show-user")
def show_user(name: str = typer.Argument(...)):
    async def _inner():
        from sqlalchemy import or_, select
        from sqlalchemy.orm import selectinload

        from manager.models import Device, User

        settings = get_settings()

        base = settings.subscription_base_url.rstrip("/")
        root_url = base[:-4] if base.endswith("/sub") else base

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.devices))
                .where(User.name == name)
            )
            user = result.scalar_one_or_none()
            devices = None

            if user is None:
                result = await session.execute(
                    select(Device)
                    .join(Device.user)
                    .options(selectinload(Device.user))
                    .where(
                        or_(
                            Device.name == name,
                            (User.name + "-" + Device.name) == name,
                        )
                    )
                )
                matched_devices = list(result.scalars().all())

                if len(matched_devices) == 0:
                    typer.echo(f"User or device not found: {name}")
                    raise typer.Exit(1)

                if len(matched_devices) > 1:
                    typer.echo(f"Device name is ambiguous: {name}")
                    typer.echo("")
                    typer.echo("Matched devices:")
                    for device in matched_devices:
                        typer.echo(f"  {device.user.name} / {device.name} ({device.os or 'unknown OS'})")
                    typer.echo("")
                    typer.echo("Use:")
                    typer.echo("  make show-user NAME=<user-name>")
                    typer.echo("")
                    typer.echo("Example:")
                    typer.echo("  make show-user NAME=MrNykterstein")
                    raise typer.Exit(1)

                device = matched_devices[0]
                user = device.user
                devices = [device]
            else:
                devices = sorted(list(user.devices), key=lambda d: d.name.lower())

            typer.echo(f"User: {user.name}")
            typer.echo(f"Status: {'enabled' if user.enabled else 'disabled'}")
            typer.echo(f"Device limit: {user.device_limit}")
            typer.echo(f"Devices shown: {len(devices)}")

            for device in devices:
                token = device.subscription_token

                typer.echo("")
                typer.echo(f"Device: {device.name} ({device.os or 'unknown OS'})")
                typer.echo(f"  status: {'enabled' if device.enabled else 'disabled'}")
                typer.echo(f"  vless_uuid: {device.vless_uuid}")

                typer.echo("")
                typer.echo("  Default / Hiddify-safe:")
                typer.echo(f"    {root_url}/sub/{token}")

                typer.echo("")
                typer.echo("  NaiveProxy:")
                typer.echo(f"    {root_url}/sub/naive/{token}")

                typer.echo("")
                typer.echo("  Hysteria2:")
                typer.echo(f"    {root_url}/sub/hysteria/{token}")

                typer.echo("")
                typer.echo("  V2RayTun / NekoBox (VLESS XHTTP+Reality, base64 URI):")
                typer.echo(f"    {root_url}/sub/v2ray/{token}")

                typer.echo("")
                typer.echo("  Xray JSON config (ручной импорт):")
                typer.echo(f"    {root_url}/sub/xray/{token}")

                typer.echo("")
                typer.echo("  Credentials:")
                typer.echo("    hidden by default; use DB/admin tooling for rotation/debug")

    run(_inner())

@app.command("remove-user")
def cli_remove_user(name: str = typer.Argument(...)):
    async def _inner():
        async with AsyncSessionLocal() as session:
            ok = await remove_user(session, name)
            await session.commit()
            typer.echo("removed" if ok else "not found")
    run(_inner())

@app.command("enable-user")
def cli_enable_user(name: str = typer.Argument(...)):
    async def _inner():
        async with AsyncSessionLocal() as session:
            ok = await set_user_enabled(session, name, True)
            await session.commit()
            typer.echo("enabled" if ok else "not found")
    run(_inner())

@app.command("disable-user")
def cli_disable_user(name: str = typer.Argument(...)):
    async def _inner():
        async with AsyncSessionLocal() as session:
            ok = await set_user_enabled(session, name, False)
            await session.commit()
            typer.echo("disabled" if ok else "not found")
    run(_inner())

@app.command("rotate-token")
def cli_rotate_token(name: str = typer.Argument(...)):
    async def _inner():
        async with AsyncSessionLocal() as session:
            device = await rotate_user_default_device_token(session, name)
            await session.commit()
            if device is None:
                typer.echo(f"User/device not found: {name}")
                raise typer.Exit(1)
            typer.echo(f"New subscription URL: {get_settings().subscription_base_url}/{device.subscription_token}")
    run(_inner())

@app.command("import-legacy")
def cli_import_legacy(file: Path = typer.Argument(..., exists=True, readable=True)):
    async def _inner():
        async with AsyncSessionLocal() as session:
            created, skipped = await import_legacy_csv(session, file)
            await session.commit()
            typer.echo(f"Legacy import done: created={created}, skipped={skipped}")
    run(_inner())

@app.command("render-configs")
def cli_render_configs():
    async def _inner():
        async with AsyncSessionLocal() as session:
            devices = await list_active_devices(session)
            render_all(devices, get_settings())
            typer.echo(f"Rendered configs for {len(devices)} active device(s)")
    run(_inner())

if __name__ == "__main__":
    app()
