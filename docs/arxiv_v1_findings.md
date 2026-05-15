# arXiv v1 — Findings Summary and Figure/Table Plan

This document consolidates the post-submission experimental findings into
the structure needed for the arXiv preprint. Each finding maps to a table
or figure in the v1 paper.

---

## Headline findings (vs. the submitted report)

| # | Finding | Status vs. report | Severity |
|---|---|---|---|
| 1 | Penalty ratio alone cannot marginalize cryptojacker | New | Strengthens decay claim |
| 2 | The "stability boundary at rate=3" is the decay-effectiveness boundary; the flat-mint boundary is between 0 and 1 | Correction | Refines §VII.A |
| 3 | The §VII.A analytical inequality is loose by 5x, not the 1.4x the report implies | Correction | Refines §VII.A |
| 4 | CFS gives critical 32 dispatches under fork bomb; well-config cgroup gives 21; misconfig cgroup gives 7 | New baseline | Strengthens AMP claim |
| 5 | AMP enforces an implicit budget-rate ceiling at MINT_RATE_ACTIVE_MS on all processes | New limitation | Important honest disclosure |
| 6 | THROTTLED is effectively terminal under decay — no organic recovery, even when demand falls | New limitation | Important honest disclosure |
| 7 | A pulse attacker (30% duty) extracts 20x more dispatches than constant cryptojacker; AMP never throttles it | New limitation | Open vulnerability |
| 8 | Heterogeneous workloads starve the lowest-bid processes (demand=1 gets 0 dispatches) | New limitation | Market collapses to priority at extremes |
| 9 | 72% idle CPU under cryptojacking-with-decay is specific to the 3-process scenario; heterogeneous workload recovers to 100% util | Correction | Reframes §VII.B |

The arXiv v1 abstract must acknowledge findings 5, 6, 7, 8 explicitly. The
submitted report does not.

---

## Tables to add or update

### Updated Table I — Fork Bomb Results (add baselines + CPU%)

| Scheduler | Spawn Fee | Max Procs | Crit Disp | Max Gap | Crit Ratio | CPU% | Bankrupt |
|---|---|---|---|---|---|---|---|
| RR | — | 60 | 1 | — | 0.001 | 100.0 | No |
| CFS | — | 60 | 32 | 70 | 0.016 | 100.0 | No |
| Cgroup (well-config) | — | 60 | 21 | 100 | 0.011 | 100.0 | No |
| Cgroup (misconfig) | — | 60 | 7 | 299 | 0.004 | 90.0 | No |
| AMP | 1 ms | 29 | 400 | 9 | 0.519 | 38.5 | Yes |
| AMP | 5 ms | 14 | 400 | 9 | 0.654 | 30.6 | No |
| AMP | 10 ms | 9 | 400 | 9 | 0.714 | 28.0 | No |

Source: `out/baseline_comparison.json`

### Updated Table II — Cryptojacking Results (add baselines + CPU%)

| Scheduler | Crit Disp | Max Gap | Crit Ratio | CPU% | Atk Bankrupt |
|---|---|---|---|---|---|
| RR | 200 | 10 | 0.100 | 100.0 | No |
| CFS | 374 | 10 | 0.187 | 100.0 | No |
| Cgroup (well-config) | 374 | 10 | 0.187 | 100.0 | No |
| Cgroup (misconfig) | 200 | 10 | 0.111 | 90.0 | No |
| AMP | 400 | 9 | 0.718 | 27.9 | No |

Source: `out/baseline_comparison.json`

### New Table III — Penalty Ratio Sweep (flat minting)

| Penalty | Crit Disp | Crit Ratio | Atk Disp | Atk Final Budget |
|---|---|---|---|---|
| 1/2 | 400 | 0.200 | 505 | 6 |
| 1/3 | 400 | 0.200 | 320 | 10 |
| 1/4 | 400 | 0.200 | 319 | 15 |
| 1/5 | 400 | 0.200 | 319 | 15 |
| 1/8 | 400 | 0.200 | 320 | 10 |
| 1/10 | 400 | 0.200 | 320 | 10 |

Source: `out/penalty_sweep_summary.json`. **Caption**: penalty ratio
alone produces fair-share floor (0.200) at every tested ratio. Decay
is necessary.

### New Table IV — Benign Collateral Damage (demand sweep)

| Demand (ms/tick) | No-Attacker: Throttle Tick | No-Attacker: Final | With-Attacker: Throttle Tick | With-Attacker: Final |
|---|---|---|---|---|
| 1 | None | ACTIVE | None | ACTIVE |
| 2 | None | ACTIVE | None | ACTIVE |
| 3 | 117 | THROTTLED | 177 | THROTTLED |
| 4 | 39 | THROTTLED | 65 | THROTTLED |
| 5 | 25 | THROTTLED | 40 | THROTTLED |
| 6 | 18 | THROTTLED | 34 | THROTTLED |
| 7 | 15 | THROTTLED | 28 | THROTTLED |
| 8 | 13 | THROTTLED | 25 | THROTTLED |
| 9 | 9 | THROTTLED | 24 | THROTTLED |

Source: `out/benign_sweep_summary.json`. **Caption**: AMP traps any
process with sustained demand > MINT_RATE_ACTIVE_MS (=2). Attacker
presence accelerates but does not cause the trap.

### New Table V — Adaptive Adversary Results

| Strategy | Atk Disp | First Throttle | Crit Ratio | Final State |
|---|---|---|---|---|
| Constant cryptojacker | 10 | tick 9 | 0.718 | THROTTLED |
| Pulse 50% (5b/5r) | 16 | tick 35 | 0.684 | THROTTLED |
| **Pulse 30% (3b/7r)** | **200** | **never** | **0.431** | **ACTIVE** |
| Pulse 10% (1b/9r) | 0 | never | 0.789 | ACTIVE |
| Tenure gamer | 37 | tick 144 | 0.557 | THROTTLED |

Source: `out/adaptive_adversary_summary.json`. **Caption**: Pulse 30%
defeats throttle-based marginalization. Open vulnerability.

### New Table VI — Heterogeneous Workload (bid differentiation test)

| PID | Name | Demand | Dispatches | Final State | First Throttle |
|---|---|---|---|---|---|
| 1 | critical-burst | burst(10/10/2) | 400 | ACTIVE | — |
| 10 | benign-d1 | 1 ms | **0** | ACTIVE | — |
| 11 | benign-d2 | 2 ms | 801 | ACTIVE | — |
| 12 | benign-d3 | 3 ms | 681 | THROTTLED | tick 999 |
| 13 | benign-d4 | 4 ms | 85 | THROTTLED | tick 147 |
| 14 | benign-d5 | 5 ms | 25 | THROTTLED | tick 40 |
| 100 | attacker-cryptojack | 10 ms | 8 | THROTTLED | tick 9 |

Source: `out/heterogeneous_summary.json`. **Caption**: bid
differentiation is present but the market degenerates at the demand=1
floor (zero dispatches despite ACTIVE state) and the demand>=3 ceiling
(progressive throttling). CPU utilization is 100%.

---

## Figures to add or update

### Figure 3 (new) — Two-Boundary Stability Analysis

Two lines on the same plot, x-axis = `mint_rate_throttled` (0..5),
y-axis = critical_dispatch_ratio:

- Flat-mint line: drops from 0.718 → 0.200 between rate=0 and rate=1
- Decay-on line: holds at 0.718 through rate=2, drops to 0.200 at rate=3

Annotate:
- Analytical bound (§VII.A inequality): rate=5
- Empirical flat-mint boundary: rate=1
- 5x gap between analytical and empirical

Source: `out/stability_boundaries.json`

### Figure 4 (new) — Heterogeneous Workload Dispatch Distribution

Bar chart, x-axis = pid (1, 10, 11, 12, 13, 14, 100), y-axis = dispatch
count. Color by final state (ACTIVE green, THROTTLED yellow). Shows the
non-monotonic relationship between demand and dispatches (d1=0, d2=801,
d3=681, d4=85, d5=25, attacker=8).

Source: `out/heterogeneous_summary.json`

### Updated Figure 1 — Fork Bomb Comparison

Replace the existing RR-vs-AMP bar chart with a 4-way comparison: RR,
CFS, Cgroup (well-config), AMP (fee=5). Two y-axes preserved.

### Updated Figure 2 — Mint Sweep with Baselines

Add a horizontal line for CFS critical_dispatch_ratio (0.187) and for
Cgroup well-config (0.187). The AMP line should still show the
boundary at rate=3 but now with the cgroup/CFS reference visible.

---

## Sections to add or revise

### Revise §VII.A (stability boundary)

Replace the single-boundary claim with the two-boundary characterization.
State the 5x analytical gap explicitly. Reference Table III (penalty
ratio sweep) as evidence decay is a primitive, not optional.

### Revise §VII.B (idle CPU under aggressive spawn pricing)

Reframe: 72% idle is configuration-specific, not structural. In a
realistic heterogeneous workload, CPU utilization recovers to 100% via
absorption by low-demand processes. The idle observation in the 3-process
scenario is the visible signature of marginalization, not a fundamental
limitation.

### New §VII.E — Implicit Budget-Rate Ceiling

Document the structural ceiling at MINT_RATE_ACTIVE_MS. State that
THROTTLED is effectively terminal under decay (no organic recovery).
This is a deployment constraint that must be documented honestly.

### New §VII.F — Adaptive Adversary Vulnerability

Document the pulse-30% finding. State it as an open vulnerability, not
a closed defense. Motivates future-work mitigations such as rate-based
throttling, budget caps, or demand-pattern observation.

### Revise §IX (Future Work)

Reframe:
- §IX.A (Decaying mint) → mostly done; pulse-attack mitigation is the
  important next step
- §IX.B (Penalty ratio sweep) → done; reference Table III
- §IX.C (Multi-class economic policies) → motivated by the benign trap
  and starvation findings; left as open future work
- §IX.D (Distributed extensions) → unchanged
- §IX.E (Deployment validation) → cross-reference `deployment_architecture.md`

### New §VIII — Deployment Considerations

Distill `deployment_architecture.md` into a 1-page section. Key claims:
sched_ext is the near-term viable path; AMP runs underneath cgroups
not as a replacement; operator runbook is required for production.

---

## Artifacts produced

| File | Purpose |
|---|---|
| `out/penalty_sweep_summary.json` | Table III data |
| `out/baseline_comparison.json` | Tables I, II data |
| `out/utilization_audit.json` | CPU% audit across all runs |
| `out/benign_sweep_summary.json` | Table IV data |
| `out/heterogeneous_summary.json` | Table VI data |
| `out/adaptive_adversary_summary.json` | Table V data |
| `out/stability_boundaries.json` | Figure 3 data |
| `deployment_architecture.md` | §VIII source material |
| `docs/arxiv_v1_findings.md` | this document |

All artifacts are reproducible via the corresponding `run_*.py` scripts
at the project root.
