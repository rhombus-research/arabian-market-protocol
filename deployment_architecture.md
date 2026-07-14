# AMP Deployment Architecture

This document describes how the Arabian Market Protocol would map onto a Linux
production deployment. It complements the simulation results by addressing a
natural follow-on question: *how would this solution be deployed to guard
against the kinds of attacks that motivate it?*

The simulation defines protocol semantics. This document defines the
integration surface.

---

## 1. Deployment paths, in order of decreasing fidelity

| Path | Kernel changes | Production-ready | Effort |
|---|---|---|---|
| Native scheduler class | Yes — new `sched_class` | Long-term goal | 6–12 months |
| sched_ext (BPF scheduler) | None — loadable BPF program | Near-term viable on Linux 6.12+ | 2–3 months |
| cgroup + eBPF probe prototype | None | Limited fidelity, fastest path | 3–4 weeks |

The recommended deployment path is **sched_ext**: it preserves the per-tick
scheduling decision while requiring no kernel fork. The cgroup+eBPF prototype
is a fallback for environments where sched_ext is not available.

---

## 2. Sijil record extension to `task_struct`

Each schedulable task gains a fixed-size Sijil record. In the kernel:

```c
struct sijil_record {
    s32  budget_ms;             /* current execution credit balance */
    s32  spent_ms;              /* cumulative debit, monotonic */
    u8   state;                 /* AMP_ACTIVE / AMP_THROTTLED / AMP_BANKRUPT */
    s16  last_bid_ms;
    u16  throttled_dispatches;  /* monotonic counter for decay */
};
```

Total: 16 bytes per task. Embedded directly in `task_struct` (or in
`sched_ext` task-local storage). Per-tick lookups are O(1).

For sched_ext, the record lives in a BPF map keyed by `pid_t` and is updated
in the BPF program's `dispatch` and `enqueue` callbacks.

---

## 3. Spawn fee enforcement at `clone()` / `fork()`

The simulation's `forkbomb_spawn` operation maps to interception of
`kernel_clone()`. Two implementation options:

**LSM hook (preferred)**: a Linux Security Module's `task_alloc` or
`bprm_creds_for_exec` hook can refuse process creation when the parent's
Sijil budget is insufficient. The hook returns `-ENOMEM` (or a new
`-EAMPBUDGET` errno) and the child is never instantiated.

**sched_ext init_task callback**: less clean — the child is partially
constructed before the policy can refuse it — but does not require a
new LSM. Suitable as a transition state.

The fee debit (`parent.budget -= SPAWN_FEE_MS`) is atomic with respect to
the parent's other budget operations: use a per-task spinlock or RCU
read-side fast path on the Sijil record.

---

## 4. Mint and reconcile on the scheduler tick

Linux scheduler tick (`scheduler_tick()` on `CONFIG_HZ` interrupt) fires
every 1–10ms depending on configuration. Map AMP phases as follows:

1. **Reconcile** — In `scheduler_tick`, before pick_next_task, walk runnable
   tasks and update state based on current budget. Cheap: only state-class
   reads, no allocations.

2. **Mint** — Right after reconcile, increment budget per state. For
   sched_ext, this is a small BPF program executed on tick.

3. **Select** — Replace `pick_next_task` for the AMP scheduling class. The
   bid computation (Section III-A of the paper) is a single multiply and
   compare per runnable task. Cost is O(n) per tick where n is the runnable
   set size, dominated by the bid comparison loop. Comparable to CFS's
   O(log n) red-black tree insertion but with a higher constant.

4. **Dispatch** — Existing kernel infrastructure handles context switch and
   accounting. The Sijil debit on grant is done in `put_prev_task`.

---

## 5. Performance overhead model

| Operation | Cost | Frequency |
|---|---|---|
| Reconcile (per task) | 1 read, 1 compare, 1 write | per tick × runnable count |
| Mint (per task) | 1 read, 1 add, 1 write | per tick × runnable count |
| Select bid | 1 read, 1 mul, 1 cmp | per task per pick |
| Debit | 1 sub, 1 cmp | per dispatch |
| Spawn fee | 1 cmp, 1 sub | per clone() |

For a runnable set of 100 tasks on a 1000Hz tick, the steady-state overhead
is approximately 300k bid-evaluations/sec — well below CFS's per-tick cost
in practice. The principal performance concern is **cache locality** of
the Sijil records; co-locating them with the rest of `task_struct`
(rather than a separate allocation) is required for parity with CFS.

A formal microbenchmark against CFS on the same workload is **future work**
and is the most important quantitative gap between the current simulation
and a deployment claim.

---

## 6. Mapping AMP guarantees to deployment scenarios

### 6.1 Fork bomb defense in a container runtime

A containerized workload (Kubernetes pod, systemd-nspawn unit) with a fork
bomb inside it would normally be bounded by the runtime's PID limit and
cgroup CPU quota. AMP adds:

- **Per-process spawn cost** — even within the PID limit, an attacker who
  fragments their initial budget cannot expand it.
- **Critical workload protection across cgroups** — the simulation's
  baseline comparison shows that a misconfigured cgroup (attacker shares
  group with critical) gives critical 7 dispatches out of 2000. AMP gives
  critical 400, regardless of cgroup assignment.

Deployment: AMP runs underneath cgroups, not as a replacement. cgroups
provide group-level isolation; AMP provides per-process economic
enforcement within and across groups.

### 6.2 Cryptojacking defense in a multi-tenant VM

A noisy-neighbor VM or container running a cryptojacker would normally
consume its full proportional share under CFS. AMP marginalizes the
saturating process at tick 9 (90ms of wall clock at TICK_MS=10).

Practical caveat from the adaptive adversary experiment: a *pulsing*
cryptojacker that modulates demand (30% duty cycle) can avoid throttling
indefinitely while still extracting substantial CPU. This is an open
vulnerability in the current protocol — not solved by AMP today, and the
deployment story must disclose it. Mitigation is future work.

### 6.3 Benign workload accommodation

The simulation reveals a deployment constraint that does not appear in the
final report: **AMP enforces an implicit budget-rate ceiling at
`MINT_RATE_ACTIVE_MS`**. Any process with mean demand exceeding this rate
will eventually drift into THROTTLED. Under the current decay mechanism,
THROTTLED is effectively terminal — the process cannot organically recover
even if its demand later falls below the ceiling.

Deployment implication: **the active mint rate must be configured to exceed
the mean demand of the largest-mean legitimate workload class on the
system, with margin**. A workload audit is a deployment precondition,
not an implementation detail. This is the strongest argument for a
deployment-time profiling tool.

---

## 7. Failure modes and operator runbook

| Symptom | Likely cause | Operator action |
|---|---|---|
| Critical process throttled | Mean demand > MINT_RATE_ACTIVE_MS | Raise active mint rate; profile demand |
| Legitimate workload trapped in THROTTLED | Transient demand spike, no recovery | Manual budget refresh |
| Spawn fee enforcement returns ENOMEM under load | Burst of legitimate forks during peak | Raise initial budget for known-trusted parents (e.g., init, sshd) |
| CPU utilization drops under attack | Marginalization engaged, no eligible work | Expected — not a regression. Verify via state-transition log |
| Pulse adversary undetected | Demand pattern stays below throttle trigger | Open issue. Mitigation is future work |

---

## 8. Telemetry surface

Required observability for safe deployment:

- Per-task: current state (ACTIVE/THROTTLED/BANKRUPT), budget, spent,
  consecutive_throttled_dispatches.
- Per-class aggregates: count by state, dispatch rate, throttle rate.
- Event log: state transitions, spawn fees paid, mint events at threshold.
- Per-tick CPU utilization with breakdown (active dispatches, throttled
  dispatches, idle from marginalization, idle from no demand).

Idle CPU under attack is a security signal, not a performance problem.
Telemetry must distinguish "idle because no work" from "idle because
adversary refused service" — these have different operator responses.

---

## 9. What is NOT addressed in the current design

- **Cross-node coordination.** Multi-tenant cloud deployments span hosts.
  Budget migration on process migration, cross-node spawn fee enforcement,
  and identity stability across scheduling domains are unresolved and
  left as future work.
- **Budget recovery.** No organic recovery from THROTTLED or BANKRUPT.
  Deployment requires either operator-mediated rehabilitation or a
  protocol extension.
- **Pulse-attack mitigation.** As characterized in
  `out/adaptive_adversary_summary.json`, demand-modulating attackers
  defeat throttle-only marginalization.
- **Heterogeneous starvation.** The heterogeneous-workload experiment
  shows that processes with very low demand (1ms/tick) can lose every bid
  to medium-demand processes and starve despite remaining ACTIVE. The
  market mechanism does not guarantee minimum service for low-bid
  workloads.
- **Formal CFS overhead comparison.** No microbenchmark exists. The
  performance model in §5 is structural, not measured.

Each is an explicit future-work item. Listing them here makes the
deployment claim falsifiable rather than aspirational.
