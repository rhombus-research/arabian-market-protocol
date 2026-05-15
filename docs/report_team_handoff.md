# arXiv v1 — Report Team Handoff

**From:** Engineering
**To:** Report writing team
**Branch:** `arxiv-v1` (off practicum HEAD; do not modify `main`)
**Scope:** convert the submitted practicum report into a clean professional
arXiv preprint that incorporates post-submission experimental findings

This document tells you what to change, what to add, and what to leave alone.
It does not tell you how to write — voice and structure are yours. Engineering
will not draft prose; we will review changes against the data.

---

## What you are working from

### Source document
- The submitted practicum report PDF (archival; do not edit in place).
- Open it side-by-side with this handoff and `docs/arxiv_v1_findings.md`.

### Authoritative data
Every numeric claim in the new paper must trace to one of these files.
If a number does not appear in one of these JSONs, do not write it.

| File | Tables / figures it sources |
|---|---|
| `out/baseline_comparison.json` | Tables I, II (revised) |
| `out/penalty_sweep_summary.json` | Table III (new) |
| `out/benign_sweep_summary.json` | Table IV (new) |
| `out/adaptive_adversary_summary.json` | Table V (new) |
| `out/heterogeneous_summary.json` | Table VI (new) |
| `out/stability_boundaries.json` | Figure 3 (new) |
| `out/utilization_audit.json` | CPU% column across all tables |
| `out/mint_sweep_summary.json` | Figure 2 (revised) — already in repo |
| `out/forkbomb_summary.json`, `out/cryptojacking_summary.json` | Existing report numbers — leave as-is |

### Planning document
- `docs/arxiv_v1_findings.md` is the table/figure plan with every cell
  pre-filled from the JSONs above. Use it as the source of truth for
  *what goes in each table*. Use the JSONs as the source of truth for
  *every number*.

### Deployment material
- `deployment_architecture.md` (project root) is the source for the new
  §VIII Deployment Considerations section. Compress it to ~1 page of
  prose; do not copy verbatim.

---

## Sections to change, by edit type

### KEEP (no changes)
- Title, author, affiliation
- Abstract paragraph 1 (problem framing) and paragraph 2 (AMP overview)
- §II Background and Related Work
- §III Protocol Semantics (entire section)
- §IV Architectural Design subsections A, B
- §V Methodology, subsections A, B, C
- §VI.A, §VI.B, §VI.C, §VI.D Fork bomb and cryptojacking results
- §VII.C (cgroup mapping)
- §VII.D (kernel integration scope)
- All references except add new ones for any related-work additions
- AI disclosure (update to cover this work)

### REVISE (existing text needs material change)

**Abstract paragraph 3 (results summary)** — append two sentences
acknowledging the implicit budget-rate ceiling finding and the
pulse-adversary open vulnerability. Do not bury these; reviewers will.

**§VI.E Two-Class Result** — keep the claim, but note that the
"cryptojacker permanently marginalized" outcome is conditional on the
attacker submitting constant maximum demand. Cross-reference §VII.F.

**§VII.A Minting Stability Boundary** — the existing single-boundary
narrative is misleading. Replace with a two-boundary characterization:

1. Flat-mint boundary at rate=0 vs rate=1 (any non-zero flat minting
   defeats throttle-only marginalization)
2. Decay-effectiveness boundary at rate=2 vs rate=3 (where decay fails
   to outpace the configured mint rate)

State explicitly that the analytical inequality in the submitted report
predicts a boundary at rate=5 but the empirical boundary is rate=1 —
**a 5x gap**. The submitted report implies ~1.4x; that is incorrect.
The empirical boundary is the operative deployment constraint.

Cite Table III (penalty ratio sweep) as evidence that decay is a
necessary protocol primitive, not an optional refinement.

**§VII.B Idle CPU Under Aggressive Spawn Pricing** — reframe. The 72%
idle figure is configuration-specific, not structural. In the
heterogeneous workload experiment (Table VI), CPU utilization recovers
to 100% as low-demand processes absorb idle cycles. The idle observation
in the 3-process scenario is the visible signature of marginalization.

**§IX Future Work** — Rewrite per the structure in
`docs/arxiv_v1_findings.md` ("Revise §IX"). Subsection priorities change:
pulse-attack mitigation rises to first place; penalty ratio sweep moves
to "done" with reference to Table III.

**Appendix A** — already discloses the PR4/PR5 bankruptcy discrepancy.
Add a sentence noting that the arXiv version corrects two additional
items from the submitted report: the stability-boundary characterization
(§VII.A) and the idle-CPU framing (§VII.B). Specificity matters.

### ADD (new sections)

**§VII.E Implicit Budget-Rate Ceiling (new)** — one or two paragraphs.
Source: `out/benign_sweep_summary.json` (sub-experiments a, b).
Key claim: AMP enforces a structural ceiling at MINT_RATE_ACTIVE_MS.
Any process with sustained mean demand above this rate enters THROTTLED
and is permanently trapped under decay — attacker or not. This is a
deployment constraint, not a defect. Cite Table IV.

**§VII.F Adaptive Adversary Vulnerability (new)** — one or two paragraphs.
Source: `out/adaptive_adversary_summary.json`. Key claim: a pulse
attacker at 30% duty cycle (3 burst ticks, 7 rest) extracts 200
dispatches over the simulation window without ever entering THROTTLED.
Critical dispatch ratio falls from 0.718 (constant attacker) to 0.431.
This is an open vulnerability in the current protocol. Frame
constructively: motivates rate-based throttling and budget caps as
future work, not a closed defense. Cite Table V.

**§VIII Deployment Considerations (new)** — ~1 page. Source:
`deployment_architecture.md`. Cover sched_ext as the near-term viable
path, the spawn-fee enforcement point (LSM hook), the performance
overhead model, and the operator runbook for the limitations disclosed
in §VII.E, §VII.F. Do not promise a kernel-level implementation; this
section is forward-looking architecture, not a delivered prototype.

Renumber the existing §VIII Conclusion to §IX, and §IX Future Work to §X.

---

## Tables and figures, by status

| Table/Fig | Status | Source | Notes |
|---|---|---|---|
| Table I | Revise | `baseline_comparison.json` | Add CFS, Cgroup (well-config), Cgroup (misconfig) rows. Add CPU% column. |
| Table II | Revise | `baseline_comparison.json` | Same additions as Table I |
| Table III | New | `penalty_sweep_summary.json` | Penalty ratio sweep, flat minting |
| Table IV | New | `benign_sweep_summary.json` | Benign demand sweep, with and without attacker |
| Table V | New | `adaptive_adversary_summary.json` | Adaptive adversary results |
| Table VI | New | `heterogeneous_summary.json` | Heterogeneous workload, 7 processes |
| Figure 1 | Revise | `baseline_comparison.json` | Add CFS, Cgroup bars |
| Figure 2 | Revise | `mint_sweep_summary.json` + `baseline_comparison.json` | Add CFS, Cgroup reference lines |
| Figure 3 | New | `stability_boundaries.json` | Two-boundary plot with 5x annotation |
| Figure 4 | New (optional) | `heterogeneous_summary.json` | Dispatch distribution bar chart |

All exact values are in `docs/arxiv_v1_findings.md`. Cross-check against
the JSONs before publication — the JSONs are authoritative.

---

## Style notes specific to this revision

1. **Honesty discipline.** This revision adds two limitations that the
   submitted report does not name (implicit ceiling, pulse vulnerability)
   plus two corrections (stability boundary, idle CPU framing). Reviewers
   will notice if these are buried. Place §VII.E and §VII.F prominently;
   reference them in the abstract and conclusion.

2. **Do not use the word "novel."** Engineering will reject prose that
   inflates contributions beyond what the data supports.

3. **The 5x analytical gap is a correction.** Acknowledge it directly.
   Do not paper over it with hedge language like "we further refine the
   bound."

4. **Frame open problems as future work, not as planned implementation.**
   Do not promise specific mitigations or extensions; the paper
   characterizes what exists today.

5. **The pulse-attack finding is the strongest argument for continued
   research.** Treat it as such. A paper that discloses a non-trivial
   open vulnerability and characterizes it cleanly is stronger than a
   paper that claims complete defense.

6. **AI disclosure** must be updated to cover this revision cycle. The
   submitted disclosure is comprehensive; extend it with the
   post-submission engineering work and the report-team revisions.

---

## Process

1. Report team produces a clean v1 draft on branch `arxiv-v1`. No
   modifications to `main` (practicum archival branch).
2. Engineering reviews against the JSON artifacts before submission.
3. Updated Appendix A reflects all corrections from the submitted version.
4. Final v1 posted to arXiv. Subsequent versions are out of scope for
   this handoff.

---

## Out of scope for v1

- Mitigations for the open vulnerabilities disclosed in §VII.E and §VII.F
- Kernel-level prototype or microbenchmark
- Distributed extensions
- Workshop-specific formatting (target venue chosen after v1 review)

If the report team identifies a gap that requires new experimental data,
file it back to engineering before drafting prose around it. Do not
estimate, interpolate, or guess.
