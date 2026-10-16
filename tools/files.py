from pathlib import Path


def list_dir(path="."):
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": f"path does not exist: {path}"}
    if p.is_file():
        return {"type": "file", "name": str(p), "size": p.stat().st_size}
    items = []
    for child in sorted(p.iterdir()):
        items.append(
            {"name": child.name, "type": "dir" if child.is_dir() else "file"}
        )
    return {"path": str(p), "items": items[:200]}


def read_file(path, limit=200):
    p = Path(path).expanduser()
    if not p.is_file():
        return {"error": f"not a file: {path}"}
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"path": str(p), "lines": lines[:limit], "total_lines": len(lines)}


def write_file(path, content):
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"written": str(p), "bytes": len(content.encode("utf-8"))}


def create_dir(path):
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return {"created": str(p)}
