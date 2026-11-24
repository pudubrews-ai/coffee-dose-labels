"""Detects whether Claude-based extraction can work: `claude` CLI present and signed in.

Sign-in is checked with `claude auth status` (local, no model call, no billing).
Set LABELAPP_NO_CLAUDE=1 to simulate a machine without Claude Code.
"""
import asyncio
import json
import os
import shutil

MESSAGE = "Auto-fill unavailable — Claude Code not found or not signed in. Fill in the fields below."
COMMON = ["~/.local/bin/claude", "/opt/homebrew/bin/claude", "/usr/local/bin/claude", "~/.claude/local/claude"]

_state = {"extract": False, "reason": "Not checked yet", "path": None}
_task: asyncio.Task | None = None


def find_claude() -> str | None:
    p = shutil.which("claude")
    if p:
        return p
    for c in COMMON:
        c = os.path.expanduser(c)
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def claude_path() -> str:
    return _state["path"] or find_claude() or "claude"


async def detect() -> dict:
    if os.environ.get("LABELAPP_NO_CLAUDE") == "1":
        return {"extract": False, "reason": "Disabled by LABELAPP_NO_CLAUDE=1", "path": None}
    path = find_claude()
    if not path:
        return {"extract": False, "reason": "claude CLI not found", "path": None}
    try:
        p = await asyncio.create_subprocess_exec(
            path, "auth", "status", stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, start_new_session=True)
        try:
            out, _ = await asyncio.wait_for(p.communicate(), 10)
        except asyncio.TimeoutError:
            p.kill(); await p.wait()
            return {"extract": True, "reason": "Sign-in check timed out; assuming signed in", "path": path}
    except OSError as e:
        return {"extract": False, "reason": f"Could not run claude: {e}", "path": None}
    try:
        j = json.loads(out.decode(errors="replace"))
    except ValueError:
        # older CLI without `auth status`: cannot verify without a billable call, so assume it works
        return {"extract": True, "reason": "Could not verify sign-in; assuming signed in", "path": path}
    if j.get("loggedIn"):
        return {"extract": True, "reason": "ok", "path": path}
    return {"extract": False, "reason": "claude CLI is not signed in", "path": path}


async def _run():
    global _state
    _state = await detect()
    return _state


def start() -> asyncio.Task:
    """(Re)start a background check; callers may await the returned task."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.ensure_future(_run())
    return _task


async def get(refresh: bool = False) -> dict:
    if refresh or _task is None:
        start()
    await asyncio.shield(_task)
    return public()


def public() -> dict:
    return {"extract": _state["extract"], "reason": _state["reason"] if not _state["extract"] else "ok"}
