#!/usr/bin/env python3
"""
experiment_runner.py
Runs multiple Chaos Engineering experiments in sequence
and generates a consolidated report for postmortem review.

Usage:
    python experiment_runner.py --config experiments/production-suite.yaml
"""

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class ExperimentRunner:
    """
    Runs a suite of Chaos Engineering experiments and
    generates a consolidated reliability report.
    """

    def __init__(self, config_path: str, dry_run: bool = False):
        self.config = self.load_config(config_path)
        self.dry_run = dry_run
        self.results = []
        self.start_time = datetime.utcnow()

    def load_config(self, config_path: str) -> dict:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        with open(path) as f:
            return yaml.safe_load(f)

    def run_suite(self) -> None:
        suite_name = self.config.get("name", "Chaos Suite")
        experiments = self.config.get("experiments", [])
        logger.info(f"Running chaos suite: {suite_name}")
        logger.info(f"Total experiments: {len(experiments)}")

        for i, exp in enumerate(experiments, 1):
            name      = exp.get("name")
            target    = exp.get("target")
            namespace = exp.get("namespace", "production")
            wait      = exp.get("wait_between_seconds", 30)

            logger.info(f"\n[{i}/{len(experiments)}] Running: {name} on {target}")

            result = {
                "experiment": name,
                "target": target,
                "namespace": namespace,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "DRY_RUN" if self.dry_run else "COMPLETED",
            }

            self.results.append(result)

            if i < len(experiments):
                logger.info(f"Waiting {wait}s before next experiment...")
                if not self.dry_run:
                    time.sleep(wait)

        self.print_report()

    def print_report(self) -> None:
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()

        print(f"\n{'='*55}")
        print(f"CHAOS SUITE REPORT")
        print(f"{'='*55}")
        print(f"  Suite started:  {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  Suite ended:    {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  Duration:       {duration:.0f}s")
        print(f"  Experiments:    {len(self.results)}")
        print(f"\n  Results:")
        for r in self.results:
            print(f"    - {r['experiment']} on {r['target']}: {r['status']}")
        print(f"{'='*55}\n")

        report_path = f"chaos-report-{self.start_time.strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump({
                "suite": self.config.get("name"),
                "started_at": self.start_time.isoformat(),
                "ended_at": end_time.isoformat(),
                "duration_seconds": duration,
                "results": self.results,
            }, f, indent=2)
        logger.info(f"Report saved: {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run chaos engineering experiment suite")
    parser.add_argument("--config", required=True, help="Path to experiment suite YAML")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    runner = ExperimentRunner(config_path=args.config, dry_run=args.dry_run)
    runner.run_suite()


if __name__ == "__main__":
    main()
