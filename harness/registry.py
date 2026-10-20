"""ToolRegistry: runs a tool by name and never raises (ARCHITECTURE.md, SPEC.md section 5).

A bad call (unknown tool, wrong arguments, an error inside the tool) becomes
{"error": "..."} so the model can read it and try again.
"""
import inspect
import json


class ToolError(Exception):
    """A bad call the model can fix, such as an unknown KPI or a date outside the period."""


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, fn, description, parameters):
        self._tools[name] = {"fn": fn, "description": description, "parameters": parameters}

    def names(self):
        return list(self._tools)

    def schemas(self):
        """Tool schemas in OpenAI style; the model gateway converts them."""
        return [{"type": "function",
                 "function": {"name": name, "description": t["description"], "parameters": t["parameters"]}}
                for name, t in self._tools.items()]

    def run(self, name, args=None):
        """Run one tool and return a JSON string. Never raises."""
        try:
            return json.dumps(self._call(name, args))
        except Exception as exc:  # e.g. a result that is not JSON
            return json.dumps({"error": f"{name!r} failed: {type(exc).__name__}: {exc}"})

    def _call(self, name, args):
        tool = self._tools.get(name) if isinstance(name, str) else None
        if tool is None:
            return {"error": f"unknown tool {name!r}; use one of {', '.join(self._tools)}"}
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return {"error": "arguments must be a JSON object"}
        try:
            inspect.signature(tool["fn"]).bind(**args)
        except TypeError as exc:
            return {"error": f"bad arguments for {name}: {exc}"}
        try:
            return tool["fn"](**args)
        except ToolError as exc:
            return {"error": str(exc)}
        except Exception as exc:  # the loop must never see an exception
            return {"error": f"{name} failed: {type(exc).__name__}: {exc}"}
