"""Freeze the transparently amended batch-four rerun before inference."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system1bench.common import read, sha, write  # noqa: E402
from freeze import HERE, SOURCE  # noqa: E402


def main() -> None:
    target = HERE / "batch4_manifest.json"
    if target.exists():
        raise ValueError("Batch-four amendment already frozen")
    original = read(HERE / "manifest.json")
    if sha(HERE / "frozen.json") != original["frozen_sha256"]:
        raise ValueError("Original codebook freeze changed")
    if sha(HERE / "PROTOCOL.md") != original["protocol_sha256"]:
        raise ValueError("Original protocol changed")
    if sha(SOURCE / "frozen.json") != original["source_frozen_sha256"]:
        raise ValueError("Source cases changed")
    source_metadata = {}
    for model in ("llama31_8b_instruct", "qwen3_8b"):
        path = SOURCE / "results" / "local" / model / "metadata.json"
        metadata = read(path)
        if metadata["signature"]["batch_size"] != 4:
            raise ValueError("Source batch size is not four")
        if metadata["status"] != "DONE":
            raise ValueError("Source run incomplete")
        source_metadata[model] = sha(path)
    write(target, dict(version="domain-codebook-batch4-amendment",
                       amendment_sha256=sha(HERE / "AMENDMENT.md"),
                       corrected_runner_sha256=sha(HERE / "run_batch4.py"),
                       base_protocol_sha256=original["protocol_sha256"],
                       frozen_sha256=original["frozen_sha256"],
                       source_frozen_sha256=original["source_frozen_sha256"],
                       source_metadata_sha256=source_metadata,
                       original_batch_size=4, corrected_batch_size=4,
                       cases=144, document_groups=91))
    print("Frozen batch-four amendment:", target)


if __name__ == "__main__":
    main()
