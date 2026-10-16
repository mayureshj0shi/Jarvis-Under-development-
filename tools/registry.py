from tools import shell, files, web
from memory.retriever import Retriever


def _remember_fact(key, value):
    Retriever().remember_fact(key, value)
    return {"remembered": key}


def _remember_note(title, content, tags=None):
    Retriever().remember_note(title, content, tags)
    return {"remembered": title}


TOOLS = {
    "shell": {
        "func": shell.run_command,
        "description": (
            "Run a Windows shell command on the user's computer. "
            "args: {\"command\": \"<cmd>\"}"
        ),
    },
    "list_dir": {
        "func": files.list_dir,
        "description": "List files/folders in a directory. args: {\"path\": \".\"}",
    },
    "read_file": {
        "func": files.read_file,
        "description": "Read a text file. args: {\"path\": \"<file>\", \"limit\": 200}",
    },
    "write_file": {
        "func": files.write_file,
        "description": (
            "Write text to a file (creates dirs). "
            "args: {\"path\": \"<file>\", \"content\": \"<text>\"}"
        ),
    },
    "create_dir": {
        "func": files.create_dir,
        "description": "Create a directory. args: {\"path\": \"<dir>\"}",
    },
    "fetch_url": {
        "func": web.fetch_url,
        "description": "Fetch and read a web page. args: {\"url\": \"<url>\"}",
    },
    "web_search": {
        "func": web.web_search,
        "description": "Search the web. args: {\"query\": \"<query>\"}",
    },
    "remember_fact": {
        "func": _remember_fact,
        "description": (
            "Save a fact to long-term memory. "
            "args: {\"key\": \"<key>\", \"value\": \"<value>\"}"
        ),
    },
    "remember_note": {
        "func": _remember_note,
        "description": (
            "Save a note into the Obsidian vault memory. "
            "args: {\"title\": \"<title>\", \"content\": \"<text>\", \"tags\": [\"opt\"]}"
        ),
    },
}


def tool_prompt_block():
    lines = ["You have these tools. To use one, reply with ONLY a JSON object:"]
    lines.append('{"tool": "<name>", "args": {<arguments>}}')
    lines.append("When you have the final answer, reply with plain text (no JSON).")
    lines.append("Available tools:")
    for name, meta in TOOLS.items():
        lines.append(f"- {name}: {meta['description']}")
    lines.append(
        "For Windows file paths, ALWAYS use forward slashes, "
        "e.g. F:/Jarvis/config.yaml (never backslashes)."
    )
    return "\n".join(lines)


def build_system(persona, memory_block):
    return (
        persona
        + "\n\n"
        + (memory_block + "\n\n" if memory_block else "")
        + tool_prompt_block()
        + "\n\nWhen the user asks you to remember a fact or preference, you MUST "
        "reply with the remember_fact or remember_note tool JSON (do not just say "
        "you will remember). When you use a tool, wait for the result, then continue. "
        "Give the user a concise spoken final answer."
    )


import tools.plugins  # registers plugin tools (e.g. weather) into TOOLS
