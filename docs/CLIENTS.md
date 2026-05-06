# Client setup

This document describes how to connect to a TryKuhnVpn server from each
supported platform.

## Subscription URL formats

The server provides a subscription URL per user, in four formats:

| Format | Query | Content-Type | Audience |
|---|---|---|---|
| Base64 VLESS link (default) | _none_ | `text/plain` | V2RayTun, v2rayN, v2rayNG, Hiddify Next |
| xray-core JSON | `?format=xray` | `application/json` | Xray CLI |
| sing-box JSON | `?format=sing-box` | `application/json` | sing-box CLI, NekoBox |
| **Clash YAML** | **`?format=clash`** | `text/yaml` | **Clash Verge Rev, CMFA, Stash** |

For **smart routing** (RU sites direct, international through VPN, ads
blocked), use `?format=clash` with a Mihomo-family client. This is the
recommended path on every platform except where noted below.

For plain full-tunnel VPN with no smart routing, the default base64 link
works in any modern Xray-family client.

## Recommended client per platform

### Windows / macOS / Linux

**Clash Verge Rev** — open-source, actively maintained, Mihomo-based.

1. Download from
   <https://github.com/clash-verge-rev/clash-verge-rev/releases/latest>.
2. Install (`.msi` on Windows, `.dmg` on macOS, `.deb`/`.rpm`/AppImage
   on Linux).
3. Open the app → **Profiles** → **+** → **Remote**.
4. Paste your subscription URL with `?format=clash` appended.
5. Activate the profile (click it).
6. On the main view, find the **PROXY** group and select **TryKuhnVpn**.
7. Enable **TUN Mode** (toggle at the bottom). System Proxy mode also
   works for browsers but **not for Telegram desktop or other apps that
   ignore the system proxy** — TUN is recommended.

### Android

**Clash Meta For Android (CMFA)** — official Mihomo-based Android client.

1. Download `cmfa-X.Y.Z-meta-universal-release.apk` from
   <https://github.com/MetaCubeX/ClashMetaForAndroid/releases/latest>.
2. Install (you may need to allow installation from unknown sources).
3. Open the app → **Profiles** → **New Profile** → **URL**.
4. Paste your subscription URL with `?format=clash` appended.
5. Save and activate the profile.
6. Tap the start button — Android will request VPN permission, allow it.

#### Known Android quirk: Госуслуги / Мой налог VPN warnings

Some Russian government apps (Госуслуги, Мой налог) show a "VPN detected,
please disable" warning **even when the app's own traffic is routed
DIRECT** (which our config does for `geoip:RU`). This is because Android
exposes a system-wide VPN flag via `ConnectivityManager`, and these apps
read that flag regardless of how individual connections are routed.

The apps still **work** — it's just a warning. If the warning is
inconvenient, CMFA supports per-app proxy exclusion:

1. CMFA → Settings → **Access control mode** → **Blacklist (bypass)**.
2. Add Госуслуги / Мой налог to the bypass list.

Excluded apps then bypass the VPN entirely at the OS level, so the
system VPN flag doesn't apply to them.

### iOS / iPadOS

iOS has **no fully-free** Mihomo-family client as of 2026.

**Recommended: Stash** — $3.99 on App Store, actively maintained.

1. Buy & install Stash from the App Store.
2. Open Stash → **Profiles** → **Add Profile** → paste subscription URL
   with `?format=clash`.
3. Activate the profile and connect.

**Free fallback: Hiddify Next** — works for connectivity (raw VPN), but
silently strips routing rules from any subscription. RU sites will be
sent through the VPN and may not work as expected. Use the default
subscription URL (no `?format=clash`) for full-tunnel mode.

### Power users (any OS)

**sing-box CLI** applies our routing rules in full. Use
`?format=sing-box` and run `sing-box run -c config.json`.

## Verifying smart routing works

After connecting with `?format=clash`, run these checks:

| Test | Expected | What it confirms |
|---|---|---|
| Open <https://gosuslugi.ru> | Loads instantly | RU domain routes DIRECT |
| Open <https://yandex.ru>, sign in | Profile shows your real RU IP | RU traffic is direct |
| Open <https://youtube.com> | Loads, video plays | International via PROXY |
| Send a message in Telegram desktop | Sends successfully | Telegram via PROXY |
| Open any ad-heavy site | No ads visible | `category-ads-all` REJECT works |

If any test fails, check the client's **Connections** tab to see which
rule matched. The expected rules are:

- `gosuslugi.ru` → matched by `GEOIP,RU` → `DIRECT`
- `youtube.com` → falls through to `MATCH` → `PROXY`
- `web.telegram.org` or `149.154.x.x` → matched by `GEOIP,telegram` →
  `PROXY`

## Troubleshooting

### Telegram desktop stuck on "Connecting..."

Use **TUN mode** in the client (not System Proxy). Telegram bypasses
system-level HTTP/SOCKS proxies on Windows by default, so System Proxy
mode doesn't capture its MTProto traffic.

### Subscription doesn't import

Check the URL is correct and includes the `?format=clash` query
parameter. The subscription should download as YAML; you can verify by
opening the URL in a browser — you should see a YAML config starting
with `mixed-port: 7890`.

### "VPN detected" in some Russian apps

See the [Android known quirk](#known-android-quirk-госуслуги--мой-налог-vpn-warnings)
section above. This is an OS-level VPN-detection issue, not specific to
our config.