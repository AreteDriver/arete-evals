"""Command-line entry point for validating and running this suite pack."""

from __future__ import annotations

import argparse
from pathlib import Path

from arete_evals import plugin as plugin  # noqa: F401
from arete_evals.bundles import create_bundle
from arete_evals.publication import publish_bundle
from arete_evals.validation import validate_suite


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arete-evals")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate suite and fixture contracts")
    validate.add_argument("suite", type=Path)

    run = sub.add_parser(
        "run", help="run baseline and candidate into an immutable bundle"
    )
    run.add_argument("--suite", type=Path, required=True)
    run.add_argument("--out", type=Path, default=Path("runs/private"))
    run.add_argument("--mode", choices=["replay", "http", "target"], default="replay")
    run.add_argument("--baseline", default="baseline")
    run.add_argument("--candidate", default="candidate")
    run.add_argument("--revision")
    run.add_argument("--created-at")
    run.add_argument("--bundle-id")

    publish = sub.add_parser(
        "publish", help="create a review-gated public derivative of a private bundle"
    )
    publish.add_argument("bundle", type=Path)
    publish.add_argument("--out", type=Path, default=Path("runs/public"))
    publish.add_argument("--reviewed-by", required=True)
    publish.add_argument(
        "--include-outputs",
        action="store_true",
        help="include full responses only after reviewing them for public release",
    )
    publish.add_argument("--published-at")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "validate":
        result = validate_suite(args.suite)
        print(
            f"validated {result['suite']} "
            f"({result['cases']} cases, {len(result['variants'])} variants)"
        )
        return 0
    if args.command == "publish":
        bundle = publish_bundle(
            private_bundle=args.bundle,
            public_root=args.out,
            reviewed_by=args.reviewed_by,
            include_outputs=args.include_outputs,
            published_at=args.published_at,
        )
    else:
        bundle = create_bundle(
            suite_path=args.suite,
            output_root=args.out,
            baseline_name=args.baseline,
            candidate_name=args.candidate,
            mode=args.mode,
            revision=args.revision,
            created_at=args.created_at,
            bundle_id=args.bundle_id,
        )
    print(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
