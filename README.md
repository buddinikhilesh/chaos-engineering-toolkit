# chaos-engineering-toolkit

Chaos Engineering toolkit for distributed systems reliability.
Injects controlled faults to surface failure modes before production impact.
Built from real Chaos Engineering experiments run at Southwest Airlines.

## What this solves
- Surfaces hidden failure modes before they hit production
- Validates self-healing and auto-scaling behaviour under stress
- Measures actual recovery time against SLO targets
- Generates consolidated reports for postmortem review
- Systematically improves reliability through controlled experiments

## Scripts

| Script | What it does |
|---|---|
| `fault_injector.py` | Injects controlled faults into Kubernetes workloads |
| `experiment_runner.py` | Runs experiment suites and generates reports |
| `experiments/production-suite.yaml` | Sample experiment suite configuration |

## Available Experiments

| Experiment | What it tests |
|---|---|
| `pod-kill` | Self-healing — pod restart and recovery time |
| `cpu-stress` | Auto-scaling behaviour under CPU load |
| `memory-pressure` | OOM handling and memory limit enforcement |
| `network-delay` | Timeout handling and retry logic |
| `pod-failure` | Restart policies and escalation behaviour |

## Usage

```bash
# List available experiments
python fault_injector.py --list-experiments

# Run single experiment (dry run first)
python fault_injector.py --target payment-api --namespace production --experiment pod-kill --dry-run

# Run single experiment
python fault_injector.py --target payment-api --namespace production --experiment pod-kill

# Run full experiment suite
python experiment_runner.py --config experiments/production-suite.yaml --dry-run
```

## Related resume projects
- Project ChaosProof — Kubernetes reliability hardening at Southwest Airlines
- Project PulseEngine — SRE observability platform at Southwest Airlines
