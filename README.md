# Arabian Market Protocol (AMP)

[![DOI](https://zenodo.org/badge/1146851625.svg)](https://doi.org/10.5281/zenodo.21362952)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p>
  <img src="assets/lamp.png" alt="Arabian Market" width=512>
</p>

**Economic enforcement without classification: a market-based defense against
resource exhaustion attacks.**

AMP is a market-based process scheduling architecture that bounds resource
exhaustion attacks by pricing execution — without ever classifying processes as
benign or malicious. This repository contains the reference simulation and the
experiments accompanying the paper.

*A project of [Rhombus Research](https://rhombus-research.com), an independent
applied-research lab.*

---

## Abstract

Fairness-oriented CPU schedulers assume processes arrive in good faith. Resource
exhaustion attacks exploit this assumption and degrade availability through sheer
consumption. Detection-based defenses fail against unknown or adaptive
adversaries and introduce classification overhead that itself becomes an attack
surface.

AMP enforces economic constraints at the scheduling layer to bound resource
exhaustion *without* process classification. Each process holds a **Sijil**
record containing a finite execution budget. CPU time is allocated through a
bidding mechanism that debits granted execution from the process budget. Process
creation requires a **spawn fee** paid from the parent's budget, which bounds the
number of identities an adversary can introduce. Processes that exhaust their
budgets transition through defined states (`ACTIVE → THROTTLED → BANKRUPT`) and
receive no further execution at bankruptcy.

Across 2000-tick simulations against a Round Robin baseline:

- **Fork bombs** — spawn-fee enforcement caps the maximum process count at 29,
  14, and 9 for fees of 1, 5, and 10 ms (vs. 60 under Round Robin), driving the
  attacker to bankruptcy at aggressive fees. The critical process sustains 400
  dispatches (max inter-dispatch gap of 9 ticks) versus a single dispatch before
  starvation under Round Robin.
- **Cryptojacking** — the throttle mechanism marginalizes the attacker
  permanently at tick 9. The critical process sustains 400 dispatches and
  captures 71.8% of all dispatch events, versus 200 under Round Robin.

Neither outcome involves process classification. Two additional constraints are
disclosed and characterized: an implicit budget-rate ceiling that traps any
process with sustained demand above the active mint rate, and a pulse adversary
at a 30% duty cycle that evades throttle-based marginalization entirely.

## How it works

| Mechanism | Purpose |
|---|---|
| **Sijil record** | Fixed-size per-process record: budget, cumulative spend, execution state, last bid. |
| **Bidding & debit** | Each tick, one runnable process is dispatched; the granted slice is debited from its budget (capped at one slice per decision). |
| **Spawn economics** | Spawning a child costs a fee from the parent budget, bounding total identities to `initial_budget / spawn_fee`. |
| **State machine** | `ACTIVE`, `THROTTLED` (half-weight bid), `BANKRUPT` (terminal, ineligible). |
| **State-based minting** | ACTIVE processes replenish at the active rate, THROTTLED at a reduced rate, BANKRUPT never. |

Enforcement is structural: every process pays for execution, and the capacity to
pay is finite and bounded at initialization. The scheduler never needs to know
which processes are adversarial.

## Repository layout

```
amp/                  Core protocol implementation
  config.py           Tunable constants (budgets, fees, mint & throttle rates)
  sijil.py            Sijil execution record + state enum
  process.py          Process model and demand protocol
  workloads.py        Demand models (constant, burst, cryptojacking, adaptive adversaries, fork bomb)
  scheduler.py        Market scheduler and Round Robin baseline
  baselines.py        CFS / Cgroup comparison schedulers
  metrics.py          Metrics recording and summary output
main.py               Primary fork-bomb / cryptojacking / mint-sweep experiments
run_baselines.py      RR vs CFS vs Cgroup vs AMP comparison
run_benign_sweep.py   Benign-workload behavior sweep
run_adaptive.py       Adaptive-adversary (pulse / tenure-gaming) experiments
penalty_ratio_sweep.py, run_heterogeneous.py,
run_stability_boundaries.py, run_utilization_audit.py
                      Supporting parameter sweeps and audits
deployment_architecture.md  Mapping of AMP semantics onto a Linux deployment
docs/                 Findings notes and reports
out/                  Generated experiment output (JSONL + summaries)
```

## Running the experiments

Requires Python 3.10+ (standard library only — no third-party dependencies).

```bash
# Primary experiments: fork bomb, cryptojacking, mint-rate sweep
python main.py

# Baseline comparison across schedulers
python run_baselines.py

# Adaptive adversaries
python run_adaptive.py
```

Each script writes machine-readable results (JSONL and JSON summaries) to `out/`
and prints formatted tables to stdout.

## Citation

If you use this work, please cite both the paper and the archived code artifact.
Replace the `<DOI>` placeholders with the Zenodo DOIs once they are minted (cite
the Zenodo *concept* DOI for the code so it always resolves to the latest
version).

**Paper**

> Bhat, S. (2026). *Economic Enforcement Without Classification: A Market-Based
> Defense Against Resource Exhaustion Attacks.* Rhombus Research.
> DOI: [10.5281/zenodo.21362269](https://doi.org/10.5281/zenodo.21362269)

**Software**

> Bhat, S. (2026). *Arabian Market Protocol (AMP)* (Version 0.1.2) [Software].
> Rhombus Research LLC.
> DOI: [10.5281/zenodo.21362952](https://doi.org/10.5281/zenodo.21362952)

```bibtex
@misc{amp2026,
  author       = {Bhat, Sriram},
  title        = {Economic Enforcement Without Classification: A Market-Based
                  Defense Against Resource Exhaustion Attacks},
  year         = {2026},
  howpublished = {Rhombus Research},
  note         = {Code: Arabian Market Protocol (AMP)},
  doi          = {10.5281/zenodo.21362269}
}
```

## License

Released under the [MIT License](LICENSE). Copyright © 2026 Rhombus Research LLC.
