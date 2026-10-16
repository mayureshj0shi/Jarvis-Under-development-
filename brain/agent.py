import json
import re

from tools.registry import TOOLS


def _extract_json(text):
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```$", "", t)
    start = t.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(t)):
        c = t[i]
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return t[start : i + 1]
    return None


_GEMMA_RE = re.compile(r"call:(\w+)\s*(\{.*?\})\s*<tool_call\|>", re.S)
_GEMMA_RE2 = re.compile(r"call:(\w+)\s*(\{.*?\})", re.S)


def _parse_gemma(text):
    for rx in (_GEMMA_RE, _GEMMA_RE2):
        m = rx.search(text)
        if m:
            name = m.group(1)
            if name not in TOOLS:
                return None
            try:
                args = json.loads(m.group(2))
            except Exception:
                args = {}
            return {"tool": name, "args": args}
    return None


def parse_action(content):
    if not content:
        return None
    raw = _extract_json(content)
    if raw:
        try:
            obj = json.loads(raw)
        except Exception:
            obj = None
        if isinstance(obj, dict) and "tool" in obj and obj["tool"] in TOOLS:
            obj.setdefault("args", {})
            return obj
    return _parse_gemma(content)


class Agent:
    def __init__(self, llm, confirm=None, max_iter=6):
        self.llm = llm
        self.confirm = confirm or (lambda tool, args: True)
        self.max_iter = max_iter

    def _coerce_native(self, tc):
        name = (tc.get("name") or "").strip()
        if name not in TOOLS:
            return None
        try:
            args = json.loads(tc.get("arguments") or "{}")
        except Exception:
            args = {}
        return {"tool": name, "args": args}

    def _execute(self, messages, action):
        name = action["tool"]
        args = action.get("args", {}) or {}
        if not self.confirm(name, args):
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool '{name}' was denied by the user. Do not retry it; either explain or pick another approach.",
                }
            )
            return
        try:
            result = TOOLS[name]["func"](**args)
        except Exception as e:
            result = {"error": str(e)}
        messages.append(
            {
                "role": "user",
                "content": f"Result from tool '{name}':\n{json.dumps(result, ensure_ascii=False)[:4000]}",
            }
        )

    def run(self, messages):
        prev = None
        for _ in range(self.max_iter):
            msg = self.llm.chat(messages)
            content = msg.content or ""
            action = parse_action(content)
            if not action:
                return content.strip()
            name = action["tool"]
            args = action["args"]
            if prev and name == prev["tool"] and args == prev["args"]:
                messages.append(
                    {
                        "role": "user",
                        "content": "You already called this exact tool with the same "
                        "arguments. Do NOT repeat it. Provide your final answer now.",
                    }
                )
                prev = action
                continue
            prev = action
            if not self.confirm(name, args):
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool '{name}' was denied by the user. Do not retry it; either explain or pick another approach.",
                    }
                )
                continue
            try:
                result = TOOLS[name]["func"](**args)
            except Exception as e:
                result = {"error": str(e)}
            messages.append(
                {
                    "role": "user",
                    "content": f"Result from tool '{name}':\n{json.dumps(result, ensure_ascii=False)[:4000]}",
                }
            )
        return (
            "I reached the tool-call limit without a final answer. "
            "Please rephrase your request."
        )

    def run_stream(self, messages, on_token=None):
        """Like run(), but streams the final-answer tokens via on_token.
        Tool-call turns still execute; their streamed text is delivered too."""
        prev = None
        for _ in range(self.max_iter):
            prov, stream = self.llm.chat_stream(messages)
            content_parts = []
            tool_calls = []
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                    if on_token:
                        on_token(delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index if tc.index is not None else 0
                        while len(tool_calls) <= idx:
                            tool_calls.append({"name": "", "arguments": ""})
                        if tc.function and tc.function.name:
                            tool_calls[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls[idx]["arguments"] += tc.function.arguments
            content = "".join(content_parts)

            action = self._coerce_native(tool_calls[0]) if tool_calls else None
            if not action:
                action = parse_action(content)
            if not action:
                return content.strip()

            name = action["tool"]
            args = action["args"]
            if prev and name == prev["tool"] and args == prev["args"]:
                messages.append(
                    {
                        "role": "user",
                        "content": "You already called this exact tool with the same "
                        "arguments. Do NOT repeat it. Provide your final answer now.",
                    }
                )
                prev = action
                continue
            prev = action
            if not self.confirm(name, args):
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool '{name}' was denied by the user. Do not retry it; either explain or pick another approach.",
                    }
                )
                continue
            try:
                result = TOOLS[name]["func"](**args)
            except Exception as e:
                result = {"error": str(e)}
            messages.append(
                {
                    "role": "user",
                    "content": f"Result from tool '{name}':\n{json.dumps(result, ensure_ascii=False)[:4000]}",
                }
            )
        return (
            "I reached the tool-call limit without a final answer. "
            "Please rephrase your request."
        )
