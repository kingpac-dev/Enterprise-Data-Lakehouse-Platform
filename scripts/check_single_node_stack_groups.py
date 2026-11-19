"""Validate catalog membership using Compose without running containers or real secrets."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "compose" / "stack-groups.single-node.json"


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    seen = set()
    errors = []
    for environment, details in catalog["environments"].items():
        for stack in details["stacks"]:
            path = ROOT / stack["compose"]
            identity = (environment, stack["group"])
            if identity in seen or not path.is_file():
                errors.append(f"Invalid or repeated group: {environment}/{stack['group']}")
                continue
            seen.add(identity)
            contents = path.read_text(encoding="utf-8")
            # Isolate interpolation from the caller's secrets and .env values.
            fixture = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMDATA", "HOME") if key in os.environ}
            for key in re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", contents):
                if "CPU" in key:
                    fixture[key] = "1"
                elif "MEMORY" in key:
                    fixture[key] = "512M"
                elif "PORT" in key and "PORTAINER" not in key:
                    fixture[key] = "19090"
                elif key.endswith("_IP"):
                    fixture[key] = "127.0.0.1"
                elif "IMAGE" in key:
                    fixture[key] = "example.invalid/image:dummy"
                else:
                    fixture[key] = "dummy"
            command = ["docker", "compose", "--env-file", os.devnull, "-p", "stack-catalog-check",
                       "-f", str(path), "--profile", "*", "config", "--services"]
            try:
                result = subprocess.run(command, cwd=ROOT, env=fixture, text=True,
                                        capture_output=True, check=False)
            except OSError as exc:
                errors.append(f"Cannot execute Compose: {type(exc).__name__}")
                break
            if result.returncode:
                errors.append(f"Compose configuration failed: {environment}/{stack['group']}")
                errors.append(result.stderr.strip())
                continue
            actual = set(result.stdout.splitlines())
            expected = set(stack["services"])
            if actual != expected:
                errors.append(f"Service mismatch: {environment}/{stack['group']}; missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
            else:
                print(f"OK {environment}/{stack['group']}: {len(actual)} services (all profiles)")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
