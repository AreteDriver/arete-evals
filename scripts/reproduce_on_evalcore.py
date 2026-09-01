"""Run the canonical offline replay through the adopted evalcore engine."""

from __future__ import annotations

from pathlib import Path

from arete_evals import plugin as plugin  # noqa: F401
from arete_evals.bundles import create_bundle

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    bundle = create_bundle(
        suite_path=ROOT / "suites" / "structured-response-integrity.yaml",
        output_root=ROOT / "runs" / "private",
        mode="replay",
    )
    print(f"wrote reproducible replay bundle: {bundle.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
