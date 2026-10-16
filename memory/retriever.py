from memory.store import MemoryStore
from memory.obsidian import ObsidianMemory


class Retriever:
    def __init__(self):
        self.store = MemoryStore()
        self.obs = ObsidianMemory()

    def context_block(self, query=None, limit=8):
        parts = []
        if query:
            facts = self.store.search_facts(query)
        else:
            facts = self.store.recent_facts(limit)
        if facts:
            lines = "\n".join(f"- {k}: {v}" for k, v in facts)
            parts.append("Known facts about the user:\n" + lines)

        notes_ctx = self.obs.context()
        if notes_ctx:
            parts.append("Memory notes (from Obsidian vault):\n" + notes_ctx)
        return "\n\n".join(parts)

    def remember_fact(self, key, value):
        self.store.add_fact(key, value)

    def remember_note(self, title, content, tags=None):
        return self.obs.write_note(title, content, tags)
