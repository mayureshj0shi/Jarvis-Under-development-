import re
from pathlib import Path

from core.config import get_config


class ObsidianMemory:
    def __init__(self):
        cfg = get_config()["obsidian"]
        self.vault = Path(cfg["vault_path"])
        self.memdir = self.vault / cfg.get("memory_folder", "Jarvis Memory")
        self.memdir.mkdir(parents=True, exist_ok=True)

    def _path(self, title):
        safe = re.sub(r"[^\w\- ]", "", title).strip().replace(" ", "-")
        safe = safe or "note"
        return self.memdir / f"{safe}.md"

    def write_note(self, title, content, tags=None):
        p = self._path(title)
        meta = ""
        if tags:
            meta = "tags: " + ", ".join(tags) + "\n\n"
        p.write_text(f"# {title}\n\n{meta}{content}\n", encoding="utf-8")
        return str(p)

    def read_note(self, title):
        p = self._path(title)
        return p.read_text(encoding="utf-8") if p.exists() else None

    def list_notes(self):
        return [p.stem for p in self.memdir.glob("*.md")]

    def search_notes(self, query):
        res = []
        q = query.lower()
        for p in self.memdir.glob("*.md"):
            txt = p.read_text(encoding="utf-8")
            if q in txt.lower():
                res.append((p.stem, txt))
        return res

    def context(self, max_notes=5):
        notes = self.list_notes()[-max_notes:]
        out = []
        for n in notes:
            out.append(self.read_note(n))
        return "\n\n---\n\n".join(out)
