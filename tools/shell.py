import subprocess

from core.config import get_config


def is_dangerous(command):
    cfg = get_config()["tools"]
    deny = cfg.get("shell_deny", [])
    low = (command or "").lower()
    return any(d in low for d in deny) or any(
        tok in low for tok in ("del ", "rm ", "rd ", "format", "shutdown", "rdisk")
    )


def run_command(command, timeout=60):
    try:
        r = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": r.returncode,
            "stdout": r.stdout[-4000:],
            "stderr": r.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"error": f"command timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}
