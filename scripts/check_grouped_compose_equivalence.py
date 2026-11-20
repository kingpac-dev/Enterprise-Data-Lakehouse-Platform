"""Compare grouped Compose entrypoints to originals without running containers."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "compose" / "stack-groups.single-node.json"
ADDITIONAL = (
    ("compose/uat/build/compose.yml", "compose/docker-compose.uat-build.yml"),
    ("compose/prod/multi-host/node1.yml", "compose/docker-compose.prod-node1.yml"),
    ("compose/prod/multi-host/node2.yml", "compose/docker-compose.prod-node2.yml"),
    ("compose/prod/multi-host/keeper3.yml", "compose/docker-compose.prod-keeper3.yml"),
)


def first_difference(left, right, path="root"):
    if type(left) is not type(right):
        return path
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return path + " (keys)"
        for key in left:
            result = first_difference(left[key], right[key], f"{path}.{key}")
            if result:
                return result
        return ""
    if isinstance(left, list):
        if len(left) != len(right):
            return path + " (length)"
        for index, (a, b) in enumerate(zip(left, right)):
            result = first_difference(a, b, f"{path}[{index}]")
            if result:
                return result
        return ""
    return "" if left == right else path


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    pairs = [(item["grouped_compose"], item["compose"])
             for env in catalog["environments"].values() for item in env["stacks"]]
    pairs.extend(ADDITIONAL)
    failed = False
    for grouped, original in pairs:
        source = ROOT / original
        fixture = {key: os.environ[key] for key in (
            "PATH", "SYSTEMROOT", "WINDIR", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
            "PROGRAMFILES", "PROGRAMDATA", "HOME") if key in os.environ}
        for key in re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", source.read_text(encoding="utf-8")):
            if "CPU" in key:
                value = "1"
            elif "MEMORY" in key:
                value = "512M"
            elif "PORT" in key and "PORTAINER" not in key:
                value = "19090"
            elif key.endswith("_IP"):
                value = "127.0.0.1"
            elif "IMAGE" in key:
                value = "example.invalid/image:dummy"
            else:
                value = "dummy"
            fixture[key] = value
        models = []
        for path in (source, ROOT / grouped):
            command = ["docker", "compose", "--env-file", os.devnull, "-p", "catalog-test",
                       "-f", str(path), "--profile", "*", "config", "--format", "json"]
            result = subprocess.run(command, cwd=ROOT, env=fixture, capture_output=True, text=True, check=False)
            if result.returncode:
                print(f"ERROR: Compose parsing failed for {path.relative_to(ROOT)}", file=sys.stderr)
                print(result.stderr, file=sys.stderr)
                failed = True
                break
            model = json.loads(result.stdout)
            # Compose extensions are authoring metadata; included x-* blocks are
            # not promoted to the parent model and do not create resources.
            models.append({key: value for key, value in model.items() if not key.startswith("x-")})
        if len(models) == 2:
            if models[0] != models[1]:
                print(f"ERROR: grouped model differs from original: {grouped} at "
                      f"{first_difference(models[0], models[1])}", file=sys.stderr)
                failed = True
            else:
                print(f"OK: {grouped} matches {original}")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
