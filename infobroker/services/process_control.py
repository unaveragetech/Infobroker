"""Manage local MCP subprocess and Ollama (Grapevine) lifecycle helpers."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

from infobroker.assistant.ollama_client import grapevine_model, ollama_base, ollama_healthy

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
PID_FILE = DATA / "mcp_server.pid"
LOG_FILE = DATA / "mcp_server.log"

# Keep a live handle so stdin stays open (stdio MCP exits on EOF / DEVNULL).
_MCP_PROC: subprocess.Popen | None = None


def _python() -> str:
    return sys.executable


def _read_pid() -> int | None:
    try:
        if not PID_FILE.exists():
            return None
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    # Prefer in-process handle when we started it from this web app.
    global _MCP_PROC
    if _MCP_PROC is not None and _MCP_PROC.pid == pid:
        return _MCP_PROC.poll() is None
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            line = (out.stdout or "").strip()
            if not line or line.upper().startswith("INFO:"):
                return False
            # CSV: "name","pid",...
            return f'"{pid}"' in line or line.split(",")[1:2] == [f'"{pid}"']
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _tail_log(n: int = 40) -> str:
    try:
        if not LOG_FILE.exists():
            return ""
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


def mcp_status() -> dict[str, Any]:
    global _MCP_PROC
    pid = _read_pid()
    # Sync with live Popen if present
    if _MCP_PROC is not None:
        if _MCP_PROC.poll() is None:
            pid = _MCP_PROC.pid
            PID_FILE.write_text(str(pid), encoding="utf-8")
        else:
            _MCP_PROC = None
            pid = _read_pid()

    running = bool(pid and _pid_alive(pid))
    if pid and not running:
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        pid = None
        if _MCP_PROC is not None and _MCP_PROC.poll() is not None:
            _MCP_PROC = None
    return {
        "running": running,
        "pid": pid if running else None,
        "command": f"{_python()} -m infobroker.mcp_server",
        "log": str(LOG_FILE) if LOG_FILE.exists() else None,
        "cwd": str(ROOT),
        "managed": _MCP_PROC is not None and running,
    }


def mcp_start() -> dict[str, Any]:
    global _MCP_PROC
    DATA.mkdir(parents=True, exist_ok=True)
    st = mcp_status()
    if st["running"]:
        return {**st, "ok": True, "message": "MCP server already running"}

    # Clear a stale dead handle
    if _MCP_PROC is not None and _MCP_PROC.poll() is not None:
        _MCP_PROC = None

    log_f = open(LOG_FILE, "a", encoding="utf-8")  # noqa: SIM115 — kept by child + parent lifetime
    log_f.write(f"\n--- mcp_start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_f.flush()

    env = {**os.environ, "PYTHONUNBUFFERED": "1", "INFOBROKER_MCP_MANAGED": "1"}
    creationflags = 0
    if os.name == "nt":
        # NEW process group only — DETACHED_PROCESS + DEVNULL stdin made FastMCP exit.
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    try:
        _MCP_PROC = subprocess.Popen(
            [_python(), "-m", "infobroker.mcp_server"],
            cwd=str(ROOT),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,  # keep open so stdio MCP does not see EOF
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
            env=env,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "running": False,
            "pid": None,
            "message": f"Failed to spawn MCP: {exc}",
            "log": str(LOG_FILE),
            "log_tail": _tail_log(),
        }

    PID_FILE.write_text(str(_MCP_PROC.pid), encoding="utf-8")
    # Give FastMCP a moment; re-check so we don't report a false start
    for _ in range(8):
        time.sleep(0.25)
        if _MCP_PROC.poll() is not None:
            break
        if _pid_alive(_MCP_PROC.pid):
            # still running after settle
            pass
    alive = _MCP_PROC.poll() is None
    if not alive:
        code = _MCP_PROC.returncode
        _MCP_PROC = None
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return {
            "ok": False,
            "running": False,
            "pid": None,
            "message": f"MCP process exited immediately (code {code}) — see log",
            "log": str(LOG_FILE),
            "log_tail": _tail_log(),
        }
    return {
        "ok": True,
        "running": True,
        "pid": _MCP_PROC.pid,
        "message": f"MCP server started (pid {_MCP_PROC.pid})",
        "log": str(LOG_FILE),
        "managed": True,
    }


def mcp_stop() -> dict[str, Any]:
    global _MCP_PROC
    pid = _read_pid()
    if _MCP_PROC is not None and _MCP_PROC.poll() is None:
        pid = _MCP_PROC.pid

    if not pid or not _pid_alive(pid):
        if _MCP_PROC is not None:
            try:
                if _MCP_PROC.stdin:
                    _MCP_PROC.stdin.close()
            except Exception:
                pass
            _MCP_PROC = None
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return {"ok": True, "running": False, "pid": None, "message": "MCP server was not running"}

    try:
        # Close stdin first so a clean shutdown is possible
        if _MCP_PROC is not None and _MCP_PROC.stdin:
            try:
                _MCP_PROC.stdin.close()
            except Exception:
                pass
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                timeout=10,
            )
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.4)
            if _pid_alive(pid):
                os.kill(pid, signal.SIGKILL)
        if _MCP_PROC is not None:
            try:
                _MCP_PROC.wait(timeout=3)
            except Exception:
                pass
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "running": _pid_alive(pid), "pid": pid, "message": str(exc)}

    _MCP_PROC = None
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    return {"ok": True, "running": False, "pid": None, "message": "MCP server stopped"}


def mcp_restart() -> dict[str, Any]:
    stop = mcp_stop()
    time.sleep(0.35)
    start = mcp_start()
    return {
        "ok": bool(start.get("ok")),
        "running": bool(start.get("running")),
        "pid": start.get("pid"),
        "message": f"{stop.get('message')}; {start.get('message')}",
        "log": start.get("log"),
        "log_tail": start.get("log_tail") or _tail_log(),
    }


def ollama_control(action: str) -> dict[str, Any]:
    """ping | status | warm | unload | list_models"""
    action = (action or "status").strip().lower()
    base = ollama_base()
    model = grapevine_model()

    if action in {"status", "ping"}:
        h = ollama_healthy()
        return {"ok": bool(h.get("ok")), "action": action, **h, "host": base}

    if action == "list_models":
        try:
            resp = requests.get(f"{base}/api/tags", timeout=8)
            resp.raise_for_status()
            names = [m.get("name") for m in (resp.json().get("models") or [])]
            return {"ok": True, "action": action, "models": names, "model": model, "host": base}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "action": action, "error": str(exc), "host": base, "model": model}

    if action == "warm":
        try:
            resp = requests.post(
                f"{base}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"num_predict": 8},
                },
                timeout=180,
            )
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "action": action,
                    "error": resp.text[:400],
                    "model": model,
                    "host": base,
                }
            return {
                "ok": True,
                "action": action,
                "message": f"Warmed {model}",
                "model": model,
                "host": base,
                "preview": ((resp.json().get("message") or {}).get("content") or "")[:120],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "action": action, "error": str(exc), "model": model, "host": base}

    if action == "unload":
        try:
            resp = requests.post(
                f"{base}/api/generate",
                json={"model": model, "prompt": "", "keep_alive": 0},
                timeout=60,
            )
            ok = resp.status_code < 400
            return {
                "ok": ok,
                "action": action,
                "message": f"Unload requested for {model}" if ok else resp.text[:300],
                "model": model,
                "host": base,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "action": action, "error": str(exc), "model": model, "host": base}

    return {
        "ok": False,
        "error": f"Unknown action: {action}",
        "allowed": ["status", "ping", "warm", "unload", "list_models"],
    }
