"""Pinned model artifacts for offline mode.

models.lock (repo root) lists each Hugging Face repo, the exact commit revision, and the sha256
of every file we use. `fetch` downloads those files into the project-local .models/ directory
(never the user's global HF cache); `verify` re-hashes them. Runtime code only reads from
.models/ and checks hashes before loading, so an offline run can't silently pick up a different
model.

    uv run python model_store.py fetch     # network allowed, used by `make models`
    uv run python model_store.py verify
    uv run python model_store.py lock      # maintainers: re-pin and rewrite models.lock
"""

import hashlib
import json
import sys
from functools import cache
from pathlib import Path

import config

MINILM_REPO = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MINILM_FILES = [
    "onnx/model.onnx",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
    "config.json",
    "modules.json",
    "sentence_bert_config.json",
    "1_Pooling/config.json",
]


class ModelArtifactError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_lock(lock_path: Path = config.MODELS_LOCK) -> dict:
    if not lock_path.exists():
        raise ModelArtifactError(f"{lock_path} is missing")
    return json.loads(lock_path.read_text())


def snapshot_dir(repo: str, revision: str, models_dir: Path = config.MODELS_DIR) -> Path:
    return models_dir / "hub" / f"models--{repo.replace('/', '--')}" / "snapshots" / revision


def lock_entry(repo: str, lock: dict) -> dict:
    for entry in lock["models"]:
        if entry["repo"] == repo:
            return entry
    raise ModelArtifactError(f"{repo} is not in models.lock")


@cache
def verified_model_dir(repo: str = MINILM_REPO) -> Path:
    """Directory of a locked model snapshot, after checking every file's sha256."""
    entry = lock_entry(repo, load_lock())
    root = snapshot_dir(repo, entry["revision"])
    for name, expected in entry["files"].items():
        path = root / name
        if not path.exists():
            raise ModelArtifactError(f"{path} is missing; run `make models` (needs network once)")
        actual = sha256_file(path)
        if actual != expected:
            raise ModelArtifactError(f"{path} sha256 {actual} does not match models.lock {expected}")
    return root


def fetch(lock: dict) -> None:
    from huggingface_hub import hf_hub_download

    for entry in lock["models"]:
        for name in entry["files"]:
            hf_hub_download(
                repo_id=entry["repo"],
                filename=name,
                revision=entry["revision"],
                cache_dir=config.MODELS_DIR / "hub",
            )
    verify(lock)


def verify(lock: dict) -> None:
    verified_model_dir.cache_clear()
    for entry in lock["models"]:
        verified_model_dir(entry["repo"])
        print(f"ok {entry['repo']}@{entry['revision'][:12]} ({len(entry['files'])} files)")


def write_lock() -> None:
    from huggingface_hub import hf_hub_download

    files = {}
    for name in MINILM_FILES:
        path = hf_hub_download(
            repo_id=MINILM_REPO,
            filename=name,
            revision=MINILM_REVISION,
            cache_dir=config.MODELS_DIR / "hub",
        )
        files[name] = sha256_file(Path(path))
    lock = {
        "comment": "Pinned model artifacts for offline mode. Regenerate with `model_store.py lock`.",
        "models": [{"repo": MINILM_REPO, "revision": MINILM_REVISION, "files": files}],
    }
    config.MODELS_LOCK.write_text(json.dumps(lock, indent=2) + "\n")
    print(f"wrote {config.MODELS_LOCK}")


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "verify"
    try:
        if cmd == "fetch":
            fetch(load_lock())
        elif cmd == "verify":
            verify(load_lock())
        elif cmd == "lock":
            write_lock()
        else:
            print(__doc__)
            return 2
    except ModelArtifactError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
