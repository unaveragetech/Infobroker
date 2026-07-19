"""Grapevine assistant package. Import submodules directly to avoid circular loads."""

__all__ = ["hunt_once", "run_assistant", "execute_tool", "list_actions", "KEY_LINKS"]


def __getattr__(name: str):
    if name in {"hunt_once", "run_assistant"}:
        from infobroker.assistant.agent import hunt_once, run_assistant

        return {"hunt_once": hunt_once, "run_assistant": run_assistant}[name]
    if name in {"execute_tool", "list_actions", "KEY_LINKS"}:
        from infobroker.assistant import tools as t

        return {"execute_tool": t.execute_tool, "list_actions": t.list_actions, "KEY_LINKS": t.KEY_LINKS}[
            name
        ]
    raise AttributeError(name)
