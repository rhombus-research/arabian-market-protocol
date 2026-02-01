# Weekly Report 02 — Market-Based Scheduling Simulation

**Project:** Arabian Market Protocol (AMP)  
**Focus:** Simulation implementation, adversarial workloads, and initial validation

---

## 1. Scope and Objectives for This Period

The goal of this week was to transition from design specification into a working simulation capable of evaluating market-based scheduling under adversarial load. Building on the internal abstractions finalized previously, this phase focused on implementing schedulers, encoding adversarial workloads as execution patterns, and validating system behavior through controlled experiments.

The guiding question for this phase was:

> Can enforcing economic constraints at the scheduler level structurally mitigate availability attacks without relying on attack detection or heuristics?

---

## 2. Simulation Framework

A discrete, tick-based scheduling simulation was implemented in user space. At each tick:

1. Runnable processes submit execution demand
2. The scheduler selects a single process to dispatch
3. A bounded CPU slice is granted
4. Execution accounting and state transitions are applied

The simulation is intentionally single-node and deterministic, enabling repeatable experiments and controlled comparison between scheduling policies.

---

## 3. Process and Execution Model

Processes are represented using fixed abstractions consisting of:

- Process identifier (PID)
- Parameterized demand function
- Execution state (e.g., runnable, throttled, bankrupt)

Scheduler-visible execution records follow a fixed-size schema inspired by the Juno record discipline. These records maintain:

- Remaining execution budget
- Accumulated execution time
- Current execution state
- Last computed bid (market scheduler)

This design avoids dynamic state growth and ensures predictable accounting behavior.

---

## 4. Baseline Scheduler: Round Robin

A baseline fairness-oriented scheduler was implemented using a Round Robin policy. The scheduler cycles deterministically through runnable processes and allocates CPU time proportionally without regard to workload intent or economic state.

This scheduler serves as a control condition. It is not designed to mitigate adversarial behavior, but to establish expected system behavior under conventional fairness-based scheduling.

---

## 5. Market-Based Scheduler

The market-based scheduler allocates CPU time based on economic constraints rather than pure fairness. Each runnable process is assigned a finite execution budget. Scheduler selection is driven by a bid function derived from:

- Current execution demand
- Remaining budget
- Execution state (with penalties applied under throttling)

As budgets are depleted, processes transition through execution states, including throttling and eventual bankruptcy. The scheduler does not perform workload classification, attack detection, or heuristic intervention. All enforcement arises from budget exhaustion alone.

---

## 6. Design Refinement: Fork-Based Budget Evasion

During early testing, a modeling issue was identified: under a purely per-process budget model, adversarial workloads could evade enforcement by rapidly spawning new processes, each initialized with a fresh budget. This allowed attackers to mint new execution identities and bypass budget exhaustion.

Rather than modifying the scheduler to detect or restrict fork behavior, the workload model was refined to include **spawn economics**:

- Process creation incurs a spawn fee charged to the parent
- Child processes are initialized with a reduced starting budget

This refinement preserves the scheduler’s no-detection design while preventing identity-based budget evasion. The correction strengthened the adversarial model and clarified that economic enforcement must account for process creation costs, not only execution costs.

---

## 7. Parameterized Workload Generators

The simulation includes parameterized workload generators representing:

- Benign background tasks with steady, low CPU demand
- Latency-sensitive critical tasks with periodic burst behavior
- Sustained CPU saturation workloads analogous to cryptomining
- Fork-bomb-style adversarial workloads with rapid process proliferation

Workloads can be composed within a single run, enabling mixed benign and adversarial scenarios.

---

## 8. Instrumentation and Metrics

Structured instrumentation was added to record per-tick execution events in machine-readable form (JSONL). Logged data includes:

- Tick number
- Scheduler type
- Runnable process count
- Dispatched PID
- Granted execution time
- Budget and execution state updates (market scheduler)

Aggregate metrics are computed from these logs, including maximum process count, fairness indices, and critical task responsiveness. This instrumentation supports reproducible analysis and comparative evaluation.

---

## 9. Initial Validation Experiments

Two full experimental runs were conducted using identical fork-bomb workloads:

- Round Robin scheduler + fork bomb
- Market-based scheduler + fork bomb

### Observed Behavior

| Metric | Round Robin | Market-Based |
|------|------------|--------------|
| Maximum process count | 60 (cap) | 13 |
| Fork bomb self-limited | No | Yes |
| Critical task dispatches | 1 | 9 |
| Failure mode | Unbounded proliferation | Bounded degradation |

Under Round Robin scheduling, fork-style workloads caused rapid process proliferation up to the configured maximum, effectively starving critical tasks despite preserved fairness. In contrast, the market-based scheduler structurally limited proliferation through budget exhaustion. Adversarial workloads consumed their own budgets and halted, while critical tasks remained schedulable for a significantly longer duration.

These results validate the simulation environment and demonstrate that economic enforcement changes the failure mode of availability attacks.

---

## 10. Open Design Question

An open question emerging from this phase concerns **budget assignment and inheritance**. While per-process budgets combined with spawn fees are effective in this model, future work must explore whether budgets should be assigned per tenant, inherited hierarchically, or dynamically adjusted based on system conditions. This question is central to extending the approach beyond controlled simulation environments.

---

## 11. Future Work

This work evaluates market-based scheduling under controlled, user-space simulation to isolate availability behavior under adversarial load. A natural extension is to validate whether similar economic enforcement mechanisms can be approximated in real systems using OS-level resource controls. Future work could explore implementing market-inspired budget constraints using container runtimes or virtual machines via cgroups, CPU quotas, or hypervisor scheduling policies. Such an evaluation would assess the practicality, overhead, and fidelity of translating fixed-budget execution models into production environments while preserving the structural availability guarantees observed in simulation. This phase is intentionally deferred to avoid conflating scheduler semantics with infrastructure-specific effects.

---

## 12. Status Summary

- Simulation framework implemented
- Baseline and market-based schedulers operational
- Adversarial workloads encoded and validated
- Instrumentation and metrics in place
- Initial validation experiments completed

