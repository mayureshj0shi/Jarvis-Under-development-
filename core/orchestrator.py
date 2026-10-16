import msvcrt
import re
import threading
import time

from rich.console import Console
from openai import RateLimitError

from core.config import load_config, get_config
from brain.llm import LLMClient
from brain.agent import Agent
from audio.recorder import Recorder
from audio.stt import transcribe
from audio.tts import TTS
from memory.retriever import Retriever
from tools.registry import build_system
from tools import shell as shell_tool


class Orchestrator:
    def __init__(self, speak=True):
        load_config()
        self.speak = speak
        self.llm = LLMClient()
        self.recorder = Recorder()
        self.tts = TTS()
        self.retriever = Retriever()
        self.agent = Agent(self.llm, confirm=self._confirm)
        self.console = Console()
        sys_cfg = get_config()["system"]
        self.name = sys_cfg.get("name", "Jarvis")
        self.persona = sys_cfg.get("persona", "You are JARVIS, a helpful assistant.")
        self.wake = (sys_cfg.get("name", "Jarvis")).lower()
        self.messages = []
        self._ptt = False

    def _system_prompt(self):
        mem = self.retriever.context_block(limit=8)
        return build_system(self.persona, mem)

    def say(self, text):
        self.console.print(f"[bold cyan]{self.name}:[/bold cyan] {text}")
        if self.speak:
            self.tts.speak(text)

    def listen(self):
        self.console.print("[yellow]Listening...[/yellow]")
        wav = self.recorder.record_until_silence()
        return transcribe(wav)

    def _confirm(self, tool, args):
        if tool != "shell":
            return True
        cmd = args.get("command", "")
        cfg = get_config()["tools"]
        allow = cfg.get("shell_allowlist", [])
        if allow and any(a in cmd for a in allow):
            return True
        if shell_tool.is_dangerous(cmd) and not cfg.get("confirm_destructive", True):
            return False
        return self._ask_confirm(f"Run command: {cmd}?")

    def _ask_confirm(self, question):
        if self.speak:
            self.say(question + " Say yes or no.")
            ans = self.listen()
            return (ans or "").strip().lower().startswith(("y", "yes"))
        return self.console.input(f"[red]{question} (y/n): [/red] ").strip().lower().startswith(
            ("y", "yes")
        )

    def _auto_memory(self, text):
        """Deterministic memory capture so 'remember' works even if the model
        does not emit a tool call. Returns a short confirmation or ''."""
        t = text.lower().strip()
        stored = []
        if re.search(r"\bmy name is\b", t):
            m = re.search(r"my name is ([a-z0-9 ][a-z0-9 ]*)", t)
            if m:
                self.retriever.remember_fact("user_name", m.group(1).strip().title())
                stored.append("user_name")
        if re.search(r"\bi (?:like|love)\b", t):
            m = re.search(r"i (?:like|love) ([a-z0-9 ][a-z0-9 ]*)", t)
            if m:
                self.retriever.remember_fact("likes", m.group(1).strip())
                stored.append("likes")
        if t.startswith("remember"):
            fact = re.sub(r"^remember (that )?", "", text).strip().rstrip(".")
            if fact:
                self.retriever.remember_note(f"Fact {int(time.time())}", fact)
                stored.append("note")
        return stored

    def handle(self, user_text):
        self.retriever.store.add_message("user", user_text)
        self._auto_memory(user_text)
        self.messages.append({"role": "user", "content": user_text})
        conv = [{"role": "system", "content": self._system_prompt()}] + self.messages
        content = self.agent.run(conv)
        self.retriever.store.add_message("assistant", content)
        self.messages.append({"role": "assistant", "content": content})
        self.say(content)
        return content

    def process_text(self, user_text):
        """Like handle(), but no console output / TTS. Returns the reply text.
        Used by the external API."""
        self.retriever.store.add_message("user", user_text)
        self._auto_memory(user_text)
        self.messages.append({"role": "user", "content": user_text})
        conv = [{"role": "system", "content": self._system_prompt()}] + self.messages
        content = self.agent.run(conv)
        self.retriever.store.add_message("assistant", content)
        self.messages.append({"role": "assistant", "content": content})
        return content

    def stream_text(self, user_text, on_token=None):
        """Like process_text(), but streams tokens via on_token (sync callable).
        Returns the full reply text."""
        self.retriever.store.add_message("user", user_text)
        self._auto_memory(user_text)
        self.messages.append({"role": "user", "content": user_text})
        conv = [{"role": "system", "content": self._system_prompt()}] + self.messages
        content = self.agent.run_stream(conv, on_token=on_token)
        self.retriever.store.add_message("assistant", content)
        self.messages.append({"role": "assistant", "content": content})
        return content

    def _is_exit(self, text):
        return text.strip().lower() in ("exit", "quit", "stop", "goodbye")

    def _start_ptt_watcher(self):
        def watch():
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\r", "\n"):
                        self._ptt = True
                else:
                    time.sleep(0.05)

        t = threading.Thread(target=watch, daemon=True)
        t.start()

    def run_voice(self):
        self.say(f"{self.name} online. Say '{self.name}' followed by a command.")
        self.console.print(
            "[dim]Tip: press Enter any time to talk without the wake word.[/dim]"
        )
        self._start_ptt_watcher()
        while True:
            try:
                if self._ptt:
                    self._ptt = False
                    self.console.print("[dim]Push-to-talk...[/dim]")
                    cmd = self.listen()
                    if self._is_exit(cmd):
                        self.say("Goodbye.")
                        break
                    self.handle(cmd)
                    continue
                self.console.print("[dim]Waiting for wake word...[/dim]")
                heard = self.listen()
                self.console.print(f"[dim]heard:[/dim] {heard}")
                low = heard.lower()
                if self.wake not in low:
                    continue
                cmd = heard
                for w in (f"hey {self.wake}", f"ok {self.wake}", self.wake):
                    cmd = cmd.lower().replace(w, "")
                cmd = cmd.strip(" ,.;:")
                if not cmd:
                    self.say("Yes?")
                    cmd = self.listen()
                if self._is_exit(cmd):
                    self.say("Goodbye.")
                    break
                self.handle(cmd)
            except KeyboardInterrupt:
                self.say("Goodbye.")
                break
            except RateLimitError:
                self.say(
                    "I've hit the OpenRouter free-tier rate limit. "
                    "Wait for the daily reset, or set a paid model in config.yaml."
                )
            except Exception as e:
                self.console.print(f"[red]Error:[/red] {e}")
                self.say("Sorry, something went wrong.")

    def run_text(self):
        self.console.print(
            f"[bold cyan]{self.name} text mode. Type 'exit' to quit.[/bold cyan]"
        )
        while True:
            try:
                user = self.console.input("[bold green]You:[/bold green] ")
            except (EOFError, KeyboardInterrupt):
                break
            if self._is_exit(user):
                break
            self.handle(user)
