"""Command-line entry point for validating and running this suite pack."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arete-evals")
    sub = parser.add_subparsers(dest="command", required=True)
    receipts = sub.add_parser(
        "receipt", help="validate, finalize and inspect work evidence"
    )
    receipt_sub = receipts.add_subparsers(dest="receipt_command", required=True)
    finalize = receipt_sub.add_parser(
        "finalize", help="seal a draft into a new receipt"
    )
    finalize.add_argument("path", type=Path)
    finalize.add_argument("--out", type=Path, required=True)
    verify = receipt_sub.add_parser(
        "verify", help="check integrity and declared artifact bytes"
    )
    verify.add_argument("path", type=Path)
    verify.add_argument("--artifacts-root", type=Path)
    verify.add_argument("--expected-sha256")
    render = receipt_sub.add_parser(
        "render", help="render an integrity-checked receipt"
    )
    render.add_argument("path", type=Path)
    project = sub.add_parser("project", help="read-only project certification checks")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    audit = project_sub.add_parser(
        "audit", help="audit the deterministic project profile"
    )
    audit.add_argument("root", type=Path, nargs="?", default=Path("."))
    audit.add_argument("--format", choices=["text", "json"], default="text")
    audit.add_argument("--as-of", type=date.fromisoformat)
    audit.add_argument("--require-clean", action="store_true")
    audit.add_argument(
        "--strict", action="store_true", help="fail on incomplete full certification"
    )
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
    if args.command == "receipt":
        from arete_evals.project import InputError
        from arete_evals.receipts import (
            finalize_receipt,
            render_receipt,
            verify_receipt,
        )

        try:
            if args.receipt_command == "finalize":
                print(json.dumps({"sha256": finalize_receipt(args.path, args.out)}))
                return 0
            if args.receipt_command == "render":
                print(render_receipt(args.path))
                return 0
            result = verify_receipt(
                args.path,
                artifacts_root=args.artifacts_root,
                expected_sha256=args.expected_sha256,
            )
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0 if result["status"] == "PASS WITH CONDITIONS" else 1
        except InputError as exc:
            print(json.dumps({"status": "FAIL", "error": str(exc)}))
            return 1
        except OSError:
            # Do not echo untrusted values or file contents in CLI diagnostics.
            print(
                json.dumps(
                    {
                        "status": "FAIL",
                        "error": "receipt input, integrity or output validation failed",
                    }
                )
            )
            return 1

    if args.command == "project":
        from arete_evals.project import audit_project, render_audit

        result = audit_project(
            args.root, as_of=args.as_of, require_clean=args.require_clean
        )
        print(
            json.dumps(result, indent=2, sort_keys=True)
            if args.format == "json"
            else render_audit(result)
        )
        return 1 if not result["automated_gates_passed"] or args.strict else 0

    from arete_evals import plugin as plugin  # noqa: F401
    from arete_evals.bundles import create_bundle
    from arete_evals.publication import publish_bundle
    from arete_evals.validation import validate_suite

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
