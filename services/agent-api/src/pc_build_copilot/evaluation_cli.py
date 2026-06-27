from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pc_build_copilot.evaluation import (
    DEFAULT_SCENARIO_PATH,
    load_scenarios,
    run_evaluation_suite,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run PC Build Copilot canonical quality evaluations."
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=DEFAULT_SCENARIO_PATH,
        help="Path to canonical scenario JSON.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON report instead of a concise text summary.",
    )
    args = parser.parse_args(argv)

    scenarios = load_scenarios(args.scenarios)
    report = run_evaluation_suite(scenarios=scenarios)

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        _print_summary(report)

    return 0 if report.passed else 1


def _print_summary(report) -> None:
    print(
        "Quality eval: "
        f"{report.passed_count}/{report.scenario_count} passed "
        f"(catalog={report.catalog_version}, rules={report.rules_version})"
    )
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        print(
            f"{status} {result.scenario_id} {result.persona} "
            f"budget={result.budget_status.value if result.budget_status else 'n/a'} "
            f"build={result.build_status.value if result.build_status else 'n/a'} "
            f"rubric={result.rubric.total if result.rubric else 'n/a'}"
        )
        if not result.passed:
            for check in result.checks:
                if not check.passed:
                    print(f"  - {check.name}: {check.detail}")


if __name__ == "__main__":
    sys.exit(main())
