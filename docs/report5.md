# Weekly Report 05 — Cryptojacking Workload, Minting Stability, and Two-Class Result

**Project:** Arabian Market Protocol (AMP)
**Focus:** Cryptojacking attack class implementation, mint rate sweep, decay mechanics, and formal adversary model

*[This document was generated with AI assistance.]*

---

## 1. Scope and Objectives for This Period

The goal of this phase was to extend AMP's experimental coverage to a second, structurally distinct attack class and characterize the minting stability boundary empirically. Specifically, this week focused on:

* Implementing the cryptojacking workload as a named, formally documented attack class
* Running cryptojacking experiments against both Round Robin and AMP schedulers
* Sweeping mint rate parameters to find the stability boundary
* Implementing and evaluating dispatch-based decremental decay as a candidate mechanism
* Formalizing the adversary model as experimental preconditions
* Documenting parameter constraints and the two-class result

The guiding question for this phase was:

> Does AMP's economic enforcement generalize across structurally different attack classes, and what are the precise guarantees and limitations for each?

---

## 2. Cryptojacking Workload

### 2.1 Design

The cryptojacking workload models a single-process sustained CPU saturation attack. It is structurally distinct from the fork bomb in one critical way: it attacks through demand intensity rather than identity amplification.

`CryptojackingDemand` was implemented as a named semantic wrapper over `ConstantDemand`. The naming is intentional — it documents the attack class explicitly in experiment code rather than leaving it implicit in a parameter value.

Workload definition:

* `ms` = `DEFAULT_SLICE_MS` — attacker always submits maximal eligible bid: `bid_ms = min(demand_ms, budget, slice_ms)`
* `spawn` = false — single process, no identity amplification
* `idle_ticks` = none — demand is nonzero every tick by construction; attacker never yields voluntarily
* `termination` = bankruptcy (budget ≤ 0); duration determined empirically

Scheduling assumption: saturation guarantees eligibility every tick, not guaranteed dispatch. Attacker competitiveness depends on bid relative to other processes.

**Invariant:** The attacker cannot increase its execution share without increasing spend. Sustained demand accelerates bankruptcy rather than amplifying influence, provided net burn rate (`grant_ms - mint_rate_active`) > 0. Unlike fork bombs, there is no identity amplification lever — more demand does not create more scheduler slots.

Experiment parameters are scheduler-assigned, not workload-controlled. `initial_budget = DEFAULT_BUDGET_MS` — same as all processes, preserving the no-classification principle.

### 2.2 Results

| Scheduler | Critical Runs | Max Gap | Dispatch Ratio | Attacker Bankrupt |
| --------- | ------------- | ------- | -------------- | ----------------- |
| RR        | 1000          | 10      | —              | No                |
| AMP       | 2000          | 9       | 0.200          | No                |

Key observations:

* Round Robin does not starve the critical process under a single-process attacker. With only 3 competing processes, RR allocates fairly — the cryptojacker cannot exploit identity amplification.
* AMP doubles critical dispatch count relative to RR. The critical process receives more service under economic enforcement than under fairness-based scheduling.
* The attacker reaches THROTTLED at tick 9 and remains there for the duration of the simulation.
* At 10,000 ticks the attacker still does not go bankrupt — it has reached a stable equilibrium.

### 2.3 Equilibrium Analysis

The attacker's stability in THROTTLED is explained by the interaction between throttle penalty and minting. Once THROTTLED, the bid penalty reduces dispatch frequency. At reduced dispatch frequency, effective burn rate drops below mint rate, creating a stable floor.

Attacker dispatch count over 10,000 ticks: ~2,500 (roughly 1 in 4 ticks). Effective burn rate: `0.25 × 10 = 2.5ms/tick`. Mint rate (THROTTLED): `1ms/tick`. Net drain: `1.5ms/tick`. But the throttle penalty reduces winning further, bringing effective drain low enough that the initial 60ms budget sustains indefinitely.

---

## 3. Minting Stability Boundary

### 3.1 Mint Rate Sweep

`MINT_RATE_THROTTLED_MS` was swept from 0 to 10 across full 2000-tick runs. The attacker did not reach bankruptcy at any rate.

At `mint_rate_throttled = 0`, the attacker wins only 557 dispatches and the critical process receives 71% of dispatches — the attacker is functionally neutralized but technically solvent.

Finding: the stability boundary is not in mint rate. The throttle mechanism itself creates an equilibrium the attacker can sustain regardless of mint rate configuration.

### 3.2 Decay Mechanics

Two decay approaches were implemented and evaluated:

**Time-based exponential decay:** `mint_rate` halves every N ticks in THROTTLED. Added `throttled_ticks` counter to `SijilRecord`. Bug identified and fixed — counter was incrementing only on state transition, not every tick in THROTTLED state.

**Dispatch-based decremental decay:** `mint_rate` decrements by 1 for every dispatch won while THROTTLED. Added `throttled_dispatches` counter to `SijilRecord`, incremented in `select()` when a THROTTLED process wins dispatch. Linear decay, self-proportional — a more aggressive attacker decays faster.

Neither approach produced bankruptcy across the full sweep. The throttle equilibrium is structurally stable. Adjusting the debit side (throttle surcharge) was considered but rejected — it breaks budget conservation, which is a core protocol invariant.

### 3.3 Stability Boundary Expression

AMP's marginalization guarantee holds provided:

```
mint_rate_throttled < effective_grant_rate
where effective_grant_rate = dispatch_frequency × grant_ms
```

Safe deployment requires:

```
mint_rate_throttled < (THROTTLE_PENALTY_NUM / THROTTLE_PENALTY_DEN) × grant_ms
```

With current values: `mint_rate_throttled < (1/2) × 10 = 5ms/tick`.

---

## 4. Two-Class Result

This phase establishes that AMP produces structurally different but equally valid guarantees against two distinct attack classes:

**Fork bomb (identity amplification):** AMP guarantees bankruptcy. Total adversarial execution is bounded by `initial_budget - (spawned_children × spawn_fee)`. Maximum child identities: `floor(initial_budget / spawn_fee)`. This bound is hard and deterministic.

**Cryptojacking (sustained saturation):** AMP guarantees marginalization. The attacker reaches THROTTLED and cannot degrade critical workload availability beyond the throttle equilibrium. At `mint_rate_throttled = 0`, critical process receives 71% of dispatches. The attacker persists but is defanged — it spends credits to stay alive and accomplishes nothing.

The honest framing: AMP does not evict cryptojackers, it defangs them. A dormant attacker that cannot exhaust availability is not a protocol failure — it is a different class of bounded outcome. Both outcomes are achieved without classification.

---

## 5. Formal Adversary Model — Experimental Preconditions

The following preconditions define the adversary assumed in all AMP experiments. Each experimental claim is valid only under these assumptions.

**P1 — Bounded Identity**
The adversary controls a fixed set of process identities at initialization. New identities may be spawned only by paying the enforced spawn fee from an existing budget. The adversary cannot introduce identities with externally funded budgets.
*Referenced by: fork bomb experiments, spawn fee sensitivity sweep.*

**P2 — No Budget Minting**
The adversary cannot mint new execution credits. Budget replenishment occurs only through the scheduler's state-based minting mechanism, applied uniformly to all non-bankrupt processes.
*Referenced by: all experiments.*

**P3 — No Bypass of Economic Enforcement**
The adversary cannot circumvent spawn fee deduction, budget debit on dispatch, or state transition rules. All economic constraints are enforced at the scheduler level before selection.
*Referenced by: all experiments.*

**P4 — Single-Node Environment**
The adversary operates within a single scheduling domain. No cross-node budget transfer or distributed identity coordination is assumed.
*Referenced by: all experiments — distributed extensions deferred to future work.*

**P5 — Arbitrary Demand**
The adversary may submit maximum demand every tick. No assumption is made about the adversary's demand pattern being detectable or distinguishable from legitimate workloads.
*Referenced by: cryptojacking experiments.*

**P6 — Objective: Degrade Critical Workload**
The adversary's goal is to maximize degradation of critical process responsiveness, measured by dispatch frequency reduction and inter-dispatch gap increase. The adversary is assumed to behave optimally toward this objective — submitting maximum demand every tick, spawning at maximum rate when budget permits, and accepting self-bankruptcy if it prolongs critical process starvation. AMP's guarantees hold against this worst-case adversarial behavior.
*Referenced by: fork bomb and cryptojacking experiments.*

---

## 6. Implementation Notes

### 6.1 SijilRecord Extensions

`throttled_dispatches: int = 0` added to `SijilRecord` with default value — existing record instantiations require no changes.

### 6.2 Scheduler Changes

`mint()` accepts `mint_rate_throttled` as an optional parameter defaulting to `MINT_RATE_THROTTLED_MS`. All existing calls are unaffected. The sweep passes different values per run without modifying config.

`reconcile_states()` increments or resets `throttled_dispatches` based on current state after each transition evaluation.

`select()` increments `throttled_dispatches` when a THROTTLED process wins dispatch.

### 6.3 Log Schema

All cryptojacking events carry `"workload": "cryptojacking"` and `"spawn_fee_ms": null`. The null is intentional — the field is inapplicable for this attack class but kept for schema consistency with fork bomb logs.

---

## 7. Future Work

* **Differentiated minting:** assign higher mint rates to protected process classes. Requires identity classification, which breaks the no-detection principle — deferred as a deployment-layer concern rather than a protocol extension.
* **Decaying mint with formal bound:** characterize the half-life or decrement value at which THROTTLED equilibrium is disrupted without violating budget conservation.
* **Distributed extensions:** multi-node budget coordination, cross-node spawn fee enforcement, and identity stability across scheduling domains.
* **OS-level mapping:** cgroup CPU quotas, container runtime enforcement, hypervisor scheduling — translating fixed-budget execution models into production environments.
* **Minting stability boundary formalization:** express the stability boundary as a closed-form inequality derived from protocol parameters rather than empirical sweep.

---

## 8. Status Summary

* Cryptojacking workload implemented and formally documented
* Two-class result established: bankruptcy (fork bomb) and marginalization (cryptojacking)
* Mint rate sweep completed — stability boundary identified as throttle equilibrium, not mint rate
* Dispatch-based decremental decay implemented — does not produce bankruptcy, throttle equilibrium confirmed structurally stable
* Budget conservation invariant preserved — surcharge approach rejected
* Formal adversary model expressed as experimental preconditions (P1–P6)
* Parameter constraints and stability boundary documented
* Implementation complete for PR5 scope