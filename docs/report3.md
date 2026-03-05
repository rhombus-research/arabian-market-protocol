# Weekly Report 03 — Protocol Formalization and Sensitivity Analysis

**Project:** Arabian Market Protocol (AMP)
**Focus:** Protocol semantics, bounded degradation analysis, and spawn-fee sensitivity evaluation

*[This document was generated with AI assistance.]*

---

## 1. Scope and Objectives for This Period

The goal of this phase was to elevate the project from a working simulation to a formally articulated economic execution model. Specifically, this week focused on:

* Formalizing the core economic semantics underlying AMP
* Introducing parameter sensitivity experiments for spawn pricing
* Evaluating bounded degradation under adversarial pressure
* Identifying structural tradeoffs and failure modes

The guiding question for this phase was:

> Does economic enforcement structurally preserve availability under adversarial identity amplification, and under what conditions does it fail?

---

## 2. Protocol Semantics (Economic Execution Model)

The Arabian Market Protocol (AMP) enforces CPU allocation through bounded execution budgets and spawn pricing. The current simulation instantiates the following model:

### 2.1 Budget Assignment

* Each process is initialized with a fixed execution budget (`DEFAULT_BUDGET_MS`).
* Execution consumes budget in discrete slices (`DEFAULT_SLICE_MS`).
* No automatic replenishment occurs during the simulation window.

### 2.2 Execution Debit

At each tick:

* A single process is selected.
* A bounded slice is granted.
* The granted amount is debited from that process’s remaining budget.

A process with budget ≤ 0 transitions to the `BANKRUPT` state and is no longer eligible for dispatch.

### 2.3 Spawn Pricing

Process creation is economically constrained:

* Each spawn event debits the parent by a configured spawn fee (`spawn_fee_ms`).
* Children are initialized with a bounded starting budget.
* No fresh identity can mint execution capacity without cost.

This mechanism prevents unlimited budget amplification through identity proliferation.

### 2.4 State Transitions

Processes move through execution states:

* `ACTIVE` → default state
* `THROTTLED` → bid reduced via penalty factor
* `BANKRUPT` → no longer schedulable

State transitions arise solely from budget exhaustion and enforcement logic. No attack detection or heuristic classification is used.

---

## 3. Baseline Comparison: Round Robin

Round Robin (RR) was retained as a fairness-oriented control scheduler.

Under fork amplification:

* RR reaches maximum process cap (60)
* Critical workload dispatch count = 1
* Critical workload last dispatch at tick 0

This demonstrates structural starvation under adversarial identity amplification.

RR preserves fairness but does not preserve availability.

---

## 4. Spawn Fee Sensitivity Experiments

To evaluate robustness rather than cherry-picked behavior, spawn fee was varied across three values:

* `spawn_fee = 1`
* `spawn_fee = 5`
* `spawn_fee = 10`

All other parameters were held constant.

### Observed Trends

| Spawn Fee | Max Procs | Max Gap (Critical) | Dispatch Ratio | Attacker Bankrupt |
| --------- | --------- | ------------------ | -------------- | ----------------- |
| 1         | 27        | 29                 | 0.087          | Yes               |
| 5         | 13        | 19                 | 0.114          | Yes               |
| 10        | 8         | 10                 | 0.155          | Yes               |

Key observations:

* Higher spawn fees reduce maximum proliferation.
* Critical gap shrinks as spawn cost increases.
* Critical dispatch ratio increases monotonically.
* In all cases, attacker budgets exhaust (self-limiting behavior).

This demonstrates bounded degradation rather than starvation.

---

## 5. Bounded Degradation vs. Starvation

Under AMP:

* The critical workload is dispatched multiple times.
* Inter-dispatch gap remains finite.
* Adversarial workloads exhaust their budgets.

Under RR:

* Critical workload receives one dispatch.
* No structural bound on starvation exists.

This establishes a core result:

> Under bounded adversarial budgets and enforced spawn pricing, the market-based scheduler preserves non-zero service probability for critical workloads.

---

## 6. Identified Limitations and Structural Tradeoffs

This phase revealed important structural limitations.

### 6.1 Critical Self-Exhaustion

The critical process also operates under a finite budget.

In all AMP variants, the critical workload eventually exhausts its own budget and ceases execution before the simulation ends (tick ~50–51).

This is not a bug.

It reflects a design property:

* AMP enforces economic fairness uniformly.
* It does not implement protected budget classes.
* It does not include replenishment mechanisms.

Implication:

> AMP defends against adversarial amplification but does not guarantee sustained availability without a budget minting policy.

A real deployment would require:

* Periodic budget replenishment
* Reserved execution class for protected workloads
* Hierarchical budget assignment

---

### 6.2 Idle Cycles Under Aggressive Enforcement

At higher spawn fees (e.g., 10), dispatch count drops below total ticks.

This indicates:

* All processes exhaust budgets
* CPU cycles remain idle

This is a robustness tradeoff:

* Strong enforcement halts attacks aggressively
* But may underutilize CPU without replenishment policy

Thus, AMP enforces structural bounds at the cost of potential utilization loss.

---

### 6.3 Latency Metric Limitations

The waiting latency metric records delay only when a process is dispatched.

Under starvation (RR case), no additional dispatch occurs; therefore, no latency event is recorded.

This metric does not capture permanent starvation directly.

Availability is better represented by:

* Dispatch count
* Last dispatch tick
* Maximum inter-dispatch gap

Future refinement could introduce starvation-aware latency tracking.

---

## 7. Fairness vs Availability Tradeoff

Jain’s fairness index demonstrates:

* RR maintains high fairness (~0.84)
* AMP reduces fairness (~0.43–0.51)

This is expected.

AMP reallocates service based on economic state rather than proportional equality.

This reinforces the central framing:

> Fairness-oriented scheduling does not imply availability preservation under adversarial conditions.

AMP sacrifices fairness to enforce structural execution bounds.

---

## 8. Deployment Considerations

This evaluation remains simulation-based.

However, the model maps conceptually to:

* cgroup CPU quotas
* Container runtime resource enforcement
* Hypervisor-level scheduling

Barriers to deployment include:

* Identity stability across distributed nodes
* Budget minting authority design
* Protection of budget metadata from tampering
* Integration with kernel dispatch constraints

These remain future work.

---

## 9. Status Summary

* Protocol semantics articulated
* Spawn economics formally evaluated
* Sensitivity analysis completed
* Bounded degradation demonstrated
* Structural limitations identified
* Tradeoffs documented

The project now moves beyond a working simulation toward a formally reasoned economic scheduling protocol with experimentally supported behavior under adversarial load.
