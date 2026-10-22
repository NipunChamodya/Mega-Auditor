from __future__ import annotations
import json, random, threading, time, base64
from datetime import datetime, timezone
from typing import Any
import requests
from .models import LinkTarget
try:
    from Crypto.Cipher import AES
except ImportError:
    AES = None

def _b64d(value: str) -> bytes:
    value = value.replace("-", "+").replace("_", "/")
    return base64.b64decode(value + "=" * (-len(value) % 4))

def _key16(target: LinkTarget) -> bytes | None:
    if AES is None or target.key_state != "format_plausible": return None
    try:
        raw = _b64d(target.key)
        if target.kind == "folder" and len(raw) >= 16: return raw[:16]
        if len(raw) == 32: return bytes(a ^ b for a, b in zip(raw[:16], raw[16:]))
        return raw if len(raw) == 16 else None
    except (ValueError, TypeError): return None

def _decrypt_name(attr: str, key: bytes | None) -> str:
    if AES is None or not key or not attr: return ""
    try:
        raw = AES.new(key, AES.MODE_CBC, iv=bytes(16)).decrypt(_b64d(attr))
        raw = raw.rstrip(b"\0")
        if raw.startswith(b"MEGA{"): return str(json.loads(raw[4:].decode("utf-8", "replace")).get("n") or "")
    except Exception: pass
    return ""

def _node_name(node: dict, folder_key: bytes | None) -> str:
    if AES is None or not folder_key or not node.get("a") or not node.get("k"): return ""
    try:
        for entry in node["k"].split("/"):
            if ":" not in entry: continue
            encrypted = _b64d(entry.split(":", 1)[1])
            if len(encrypted) % 16: continue
            raw = AES.new(folder_key, AES.MODE_ECB).decrypt(encrypted)
            key = bytes(a ^ b for a, b in zip(raw[:16], raw[16:32])) if len(raw) >= 32 else raw[:16]
            name = _decrypt_name(node["a"], key)
            if name: return name
    except Exception: pass
    return ""

API = "https://g.api.mega.co.nz/cs"
DEAD_CODES = {-9: "deleted / not found", -8: "expired", -2: "invalid link", -11: "access denied", -14: "invalid key"}

def human(n: int | float) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB": return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"

class RateLimiter:
    def __init__(self, rate: float):
        self.interval = 1 / max(0.1, rate); self.lock = threading.Lock(); self.next = 0.0; self.cool_until = 0.0
    def wait(self) -> None:
        with self.lock:
            now = time.monotonic(); target = max(now, self.next, self.cool_until); self.next = target + self.interval
        time.sleep(max(0.0, target - now))
    def cooldown(self, seconds: float) -> None:
        with self.lock: self.cool_until = max(self.cool_until, time.monotonic() + seconds)

_local = threading.local()
def _session() -> requests.Session:
    if not hasattr(_local, "session"):
        s = requests.Session(); s.headers["User-Agent"] = "MEGA-Link-Auditor/2.0 (public-link metadata checker)"; _local.session = s
    return _local.session

def _api(limiter: RateLimiter, payload: dict[str, Any], handle: str | None = None, tries: int = 5) -> Any:
    last: Any = "network or response error"
    for attempt in range(tries):
        limiter.wait()
        try:
            params = {"id": random.randint(0, 2**31 - 1)}
            if handle: params["n"] = handle
            response = _session().post(API, params=params, data=json.dumps([payload]), timeout=(10, 45))
            if response.status_code in (429, 509):
                limiter.cooldown(min(60, 2**attempt * 3 + random.random())); last = f"HTTP {response.status_code}"; continue
            response.raise_for_status()
            body = response.json(); body = body[0] if isinstance(body, list) and body else body
            if isinstance(body, int) and body in (-3, -4, -6, -18):
                limiter.cooldown(min(60, 2**attempt * 3 + random.random())); last = f"API rate/transient code {body}"; continue
            return body
        except (requests.RequestException, ValueError) as exc:
            last = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < tries: time.sleep(min(20, 2**attempt + random.random()))
    return {"_error": str(last)}

def check_link(target: LinkTarget, limiter: RateLimiter) -> dict[str, Any]:
    base = {"id": target.id, "link": target.link, "kind": target.kind, "handle": target.handle,
            "key_state": target.key_state, "sources": sorted(target.sources), "source_count": len(target.sources),
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": 0, "size_bytes": 0,
            "name": "", "preview": []}
    data = _api(limiter, {"a": "f", "c": 1, "r": 1} if target.kind == "folder" else {"a": "g", "p": target.handle}, target.handle if target.kind == "folder" else None)
    if isinstance(data, dict) and "_error" in data:
        return {**base, "status": "ERROR", "reason": data["_error"]}
    if isinstance(data, int):
        if data == -16: status, reason = "TAKEDOWN", "MEGA returned a takedown/blocked response"
        elif data in DEAD_CODES: status, reason = "INACCESSIBLE", DEAD_CODES[data]
        else: status, reason = "ERROR", f"MEGA API code {data}; not enough evidence to call the link dead"
        return {**base, "status": status, "reason": reason}
    if not isinstance(data, dict): return {**base, "status": "ERROR", "reason": "unexpected API response shape"}
    if target.kind == "file":
        size = int(data.get("s") or 0)
        # A zero-byte file can be valid; distinguish it from a failed API response.
        count = 1
        name = _decrypt_name(str(data.get("at") or ""), _key16(target))
        return {**base, "status": "WORKING", "reason": "file metadata returned; size may legitimately be zero", "files": count, "size_bytes": size, "name": name}
    nodes = data.get("f")
    if not isinstance(nodes, list): return {**base, "status": "ERROR", "reason": "folder response did not contain a node list"}
    by_handle = {n.get("h"): n for n in nodes if isinstance(n, dict) and n.get("h")}
    root_handle = target.sub or target.handle
    root = by_handle.get(root_handle)
    if root is None and not target.sub: root = next((n for n in nodes if isinstance(n, dict) and n.get("p") not in by_handle), None)
    if root is None: return {**base, "status": "INACCESSIBLE", "reason": "requested folder node was not found in returned listing"}
    children: dict[str | None, list[dict]] = {}
    for node in nodes:
        if isinstance(node, dict): children.setdefault(node.get("p"), []).append(node)
    stack, files = [root], []
    while stack:
        node = stack.pop()
        if node.get("t") == 0: files.append(node)
        else: stack.extend(children.get(node.get("h"), []))
    size = sum(int(n.get("s") or 0) for n in files)
    folder_key = _key16(target)
    name = _node_name(root, folder_key)
    preview = []
    if folder_key:
        for node in sorted(files, key=lambda item: -int(item.get("s") or 0))[:5]:
            item_name = _node_name(node, folder_key) or "(name unavailable)"
            preview.append(f"{item_name} ({human(int(node.get('s') or 0))})")
    status = "EMPTY" if not files else "WORKING"
    return {**base, "status": status, "reason": "folder listing returned" if files else "valid folder listing contains no files", "files": len(files), "size_bytes": size, "name": name, "preview": preview}
