#!/usr/bin/env python3
"""Fetch generated registry key classes from PaperMC/Paper version branches
and emit one JSON data file per Minecraft version for the static site.

Usage: python3 scripts/fetch_data.py
Writes: data/<version>.json and data/versions.json
"""
import json
import re
import shutil
import subprocess
import tempfile
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = "PaperMC/Paper"
KEYS_DIR = "paper-api/src/generated/java/io/papermc/paper/registry/keys"

# (display version, git branch) — newest first. Each page uses only its own branch.
VERSIONS = [
    ("26.2", "main"),
    ("26.1.2", "ver/26.1.2"),
    ("1.21.11", "ver/1.21.11"),
    ("1.21.10", "ver/1.21.10"),
    ("1.21.9", "ver/1.21.9"),
    ("1.21.8", "ver/1.21.8"),
    ("1.21.5", "ver/1.21.5"),
    ("1.21.4", "ver/1.21.4"),
]

KEY_RE = re.compile(r'create\(\s*key\("([^"]+)"\)')

OUT_DIR = Path(__file__).resolve().parent.parent / "data"

# vanilla datapack tag directory -> Paper registry id (identity for unlisted dirs)
TAG_DIR_TO_REGISTRY = {
    "item": "item_type",
    "block": "block_type",
    "point_of_interest_type": "poi_type",
    "potion": "potion_type",
    "worldgen/biome": "biome",
    "worldgen/structure": "structure",
}


def get(url: str) -> bytes:
    # curl instead of urllib: python.org macOS builds lack root CA certs
    return subprocess.run(
        ["curl", "-fsSL", "--retry", "3", "-A", "paper-keys-site", url],
        check=True, capture_output=True,
    ).stdout


def branch_tree(branch: str) -> list[str]:
    url = f"https://api.github.com/repos/{REPO}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1"
    tree = json.loads(get(url))
    if tree.get("truncated"):
        raise RuntimeError(f"tree truncated for {branch}")
    return [
        e["path"]
        for e in tree["tree"]
        if e["path"].startswith(KEYS_DIR) and e["path"].endswith(".java")
    ]


def registry_id(class_name: str) -> str:
    """ItemTypeTagKeys -> item_type, ItemTypeKeys -> item_type"""
    base = re.sub(r"(Tag)?Keys$", "", class_name)
    return re.sub(r"(?<!^)(?=[A-Z])", "_", base).lower()


def registry_name(rid: str) -> str:
    return rid.replace("_", " ").title()


def parse_keys(source: str) -> list[str]:
    keys = []
    for k in KEY_RE.findall(source):
        keys.append(k if ":" in k else f"minecraft:{k}")
    return sorted(set(keys))


def fetch_tag_values(version: str) -> dict[str, dict[str, list[str]]]:
    """Vanilla tag contents per registry from misode/mcmeta's <version>-data tag.

    Returns {registry_id: {"minecraft:tag_name": [entry, ...]}}.
    """
    tmp = tempfile.mkdtemp(prefix="mcmeta-")
    try:
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", f"{version}-data",
             "--filter=blob:none", "--sparse", "https://github.com/misode/mcmeta.git", tmp],
            check=True,
        )
        subprocess.run(
            ["git", "-C", tmp, "sparse-checkout", "set", "data/minecraft/tags"],
            check=True, capture_output=True,
        )
        base = Path(tmp) / "data/minecraft/tags"
        result: dict[str, dict[str, list[str]]] = {}
        if not base.is_dir():
            return result
        for f in sorted(base.rglob("*.json")):
            parts = f.relative_to(base).parts
            # worldgen tags nest one level deeper: tags/worldgen/biome/<name>.json
            if parts[0] == "worldgen":
                tag_dir, name_parts = "/".join(parts[:2]), parts[2:]
            else:
                tag_dir, name_parts = parts[0], parts[1:]
            registry = TAG_DIR_TO_REGISTRY.get(tag_dir, tag_dir)
            tag_key = "minecraft:" + "/".join(name_parts)[: -len(".json")]
            values = []
            for v in json.loads(f.read_text()).get("values", []):
                if isinstance(v, dict):
                    v = v["id"]
                values.append(v)
            result.setdefault(registry, {})[tag_key] = values
        return result
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fetch_version(version: str, branch: str) -> dict:
    paths = branch_tree(branch)
    registries: dict[str, dict] = {}

    def load(path: str):
        class_name = Path(path).stem
        is_tag = class_name.endswith("TagKeys")
        rid = registry_id(class_name)
        source = get(f"https://raw.githubusercontent.com/{REPO}/{branch}/{path}").decode()
        return rid, is_tag, parse_keys(source)

    with ThreadPoolExecutor(max_workers=12) as pool:
        for rid, is_tag, keys in pool.map(load, paths):
            reg = registries.setdefault(
                rid, {"id": rid, "name": registry_name(rid), "keys": [], "tagKeys": []}
            )
            reg["tagKeys" if is_tag else "keys"] = keys

    tag_values = fetch_tag_values(version)
    for rid, reg in registries.items():
        vals = tag_values.get(rid, {})
        reg["tagValues"] = {k: vals[k] for k in reg["tagKeys"] if k in vals}

    ordered = sorted(registries.values(), key=lambda r: r["id"])
    return {"version": version, "branch": branch, "registries": ordered}


def main():
    OUT_DIR.mkdir(exist_ok=True)
    manifest = []
    for version, branch in VERSIONS:
        print(f"fetching {version} ({branch}) ...", flush=True)
        data = fetch_version(version, branch)
        n_keys = sum(len(r["keys"]) for r in data["registries"])
        n_tags = sum(len(r["tagKeys"]) for r in data["registries"])
        print(f"  {len(data['registries'])} registries, {n_keys} keys, {n_tags} tag keys")
        out = OUT_DIR / f"{version}.json"
        out.write_text(json.dumps(data, separators=(",", ":")))
        manifest.append({"version": version, "branch": branch, "file": f"data/{version}.json"})
    (OUT_DIR / "versions.json").write_text(json.dumps(manifest, indent=2))
    print("done")


if __name__ == "__main__":
    main()
