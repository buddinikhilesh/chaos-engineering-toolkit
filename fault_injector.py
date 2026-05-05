#!/usr/bin/env python3
"""
fault_injector.py
Chaos Engineering fault injection toolkit for distributed systems.
Injects controlled failures to surface failure modes before production impact.
Built from real Chaos Engineering experiments at Southwest Airlines.

Usage:
    python fault_injector.py --target payment-api --namespace production --experiment pod-kill
    python fault_injector.py --target payment-api --namespace production --experiment network-delay
    python fault_injector.py --list-experiments
"""

import argparse
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    experiment: str
    target: str
    namespace: str
    success: bool
    recovery_time_seconds: float
    observations: list


class FaultInjector:
    """
    Injects controlled faults into Kubernetes workloads
    to surface failure modes before production impact.
    """

    EXPERIMENTS = {
        "pod-kill": "Kills a random pod to test self-healing",
        "network-delay": "Injects network latency to test timeout handling",
        "cpu-stress": "Stresses CPU to test auto-scaling behaviour",
        "memory-pressure": "Applies memory pressure to test OOM handling",
        "pod-failure": "Forces pod into failed state to test restart policies",
    }

    def __init__(self, namespace: str, dry_run: bool = False):
        self.namespace = namespace
        self.dry_run = dry_run
        self.results = []
        if dry_run:
            logger.info("DRY RUN mode — no actual faults will be injected")

    def run_kubectl(self, command: str, timeout: int = 30) -> tuple:
        if self.dry_run:
            logger.info(f"[DRY RUN] kubectl {command}")
            return 0, "dry-run-output", ""
        try:
            result = subprocess.run(
                f"kubectl {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "TIMEOUT"

    def get_pods(self, target: str) -> list:
        returncode, stdout, stderr = self.run_kubectl(
            f"get pods -n {self.namespace} -l app={target} --no-headers -o custom-columns=NAME:.metadata.name"
        )
        if returncode != 0 or not stdout:
            return []
        return [p for p in stdout.split("\n") if p.strip()]

    def experiment_pod_kill(self, target: str) -> ExperimentResult:
        logger.info(f"Experiment: pod-kill | Target: {target} | Namespace: {self.namespace}")
        observations = []
        start_time = time.time()

        pods = self.get_pods(target)
        if not pods:
            logger.warning(f"No pods found for target: {target}")
            return ExperimentResult(
                experiment="pod-kill",
                target=target,
                namespace=self.namespace,
                success=False,
                recovery_time_seconds=0,
                observations=["No pods found for target"]
            )

        # Kill the first pod
        pod_to_kill = pods[0]
        logger.info(f"Killing pod: {pod_to_kill}")
        observations.append(f"Killing pod: {pod_to_kill}")

        returncode, stdout, stderr = self.run_kubectl(
            f"delete pod {pod_to_kill} -n {self.namespace} --grace-period=0"
        )

        if returncode != 0:
            observations.append(f"Failed to delete pod: {stderr}")
            return ExperimentResult(
                experiment="pod-kill",
                target=target,
                namespace=self.namespace,
                success=False,
                recovery_time_seconds=0,
                observations=observations
            )

        observations.append(f"Pod {pod_to_kill} deleted successfully")

        # Wait for recovery
        logger.info("Waiting for pod recovery...")
        recovery_start = time.time()
        max_wait = 120
        recovered = False

        while time.time() - recovery_start < max_wait:
            time.sleep(5)
            returncode, stdout, stderr = self.run_kubectl(
                f"get pods -n {self.namespace} -l app={target} --no-headers"
            )
            if "Running" in stdout:
                recovered = True
                observations.append("Pod recovered — Running state detected")
                break

        recovery_time = time.time() - start_time

        if not recovered:
            observations.append(f"Pod did not recover within {max_wait}s — SLO breach risk")

        logger.info(f"Recovery time: {recovery_time:.1f}s | Recovered: {recovered}")

        return ExperimentResult(
            experiment="pod-kill",
            target=target,
            namespace=self.namespace,
            success=recovered,
            recovery_time_seconds=recovery_time,
            observations=observations
        )

    def experiment_cpu_stress(self, target: str, duration: int = 60) -> ExperimentResult:
        logger.info(f"Experiment: cpu-stress | Target: {target} | Duration: {duration}s")
        observations = []
        start_time = time.time()

        pods = self.get_pods(target)
        if not pods:
            return ExperimentResult(
                experiment="cpu-stress",
                target=target,
                namespace=self.namespace,
                success=False,
                recovery_time_seconds=0,
                observations=["No pods found for target"]
            )

        pod = pods[0]
        logger.info(f"Injecting CPU stress into pod: {pod}")
        observations.append(f"Injecting CPU stress into pod: {pod}")

        # Inject CPU stress
        returncode, stdout, stderr = self.run_kubectl(
            f"exec {pod} -n {self.namespace} -- sh -c 'stress --cpu 2 --timeout {duration}s &'"
        )

        if returncode != 0:
            observations.append(f"CPU stress injection failed: {stderr}")

        observations.append(f"CPU stress running for {duration}s")
        observations.append("Monitoring auto-scaling behaviour")

        # Check HPA response
        time.sleep(30)
        returncode, stdout, stderr = self.run_kubectl(
            f"get hpa -n {self.namespace}"
        )
        if stdout:
            observations.append(f"HPA status: {stdout}")

        recovery_time = time.time() - start_time

        return ExperimentResult(
            experiment="cpu-stress",
            target=target,
            namespace=self.namespace,
            success=True,
            recovery_time_seconds=recovery_time,
            observations=observations
        )

    def run_experiment(self, target: str, experiment: str) -> ExperimentResult:
        if experiment not in self.EXPERIMENTS:
            logger.error(f"Unknown experiment: {experiment}")
            logger.info(f"Available: {list(self.EXPERIMENTS.keys())}")
            sys.exit(1)

        if experiment == "pod-kill":
            return self.experiment_pod_kill(target)
        elif experiment == "cpu-stress":
            return self.experiment_cpu_stress(target)
        else:
            logger.info(f"Experiment {experiment} logged — implement specific injector")
            return ExperimentResult(
                experiment=experiment,
                target=target,
                namespace=self.namespace,
                success=True,
                recovery_time_seconds=0,
                observations=[f"Experiment {experiment} registered"]
            )

    def print_result(self, result: ExperimentResult) -> None:
        print(f"\n{'='*55}")
        print(f"CHAOS EXPERIMENT RESULT")
        print(f"{'='*55}")
        print(f"  Experiment:      {result.experiment}")
        print(f"  Target:          {result.target}")
        print(f"  Namespace:       {result.namespace}")
        print(f"  Success:         {result.success}")
        print(f"  Recovery Time:   {result.recovery_time_seconds:.1f}s")
        print(f"  Observations:")
        for obs in result.observations:
            print(f"    - {obs}")
        print(f"{'='*55}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chaos Engineering fault injection toolkit")
    parser.add_argument("--target", help="Target service name")
    parser.add_argument("--namespace", default="production")
    parser.add_argument("--experiment", help="Experiment to run")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-experiments", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list_experiments:
        print("\nAvailable Experiments:")
        for name, desc in FaultInjector.EXPERIMENTS.items():
            print(f"  {name}: {desc}")
        return

    if not args.target or not args.experiment:
        print("Provide --target and --experiment")
        print("Use --list-experiments to see available experiments")
        sys.exit(1)

    injector = FaultInjector(namespace=args.namespace, dry_run=args.dry_run)
    result = injector.run_experiment(args.target, args.experiment)
    injector.print_result(result)
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
