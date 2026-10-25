# Attack-Aware Adaptive Security Service Orchestration for DDoS-Resilient Fog Networks

**NET 470 / NET 740 — Project 7**  
Harsh Patel & Nimrah Ashraf — DePaul University, School of Computing

---

## Overview

This repository contains the complete simulation implementation and experimental artifacts for the paper:

> *Attack-Aware Adaptive Security Service Orchestration for DDoS-Resilient Fog Networks*

The proposed **AALB (Attack-Aware Adaptive Load Balancer)** framework dynamically adapts the active security service function chain (SFC) in an NFV-enabled fog network based on real-time DDoS attack-state estimation. Three bounded security profiles — K0 ⟨LB⟩, K1 ⟨RF, LB⟩, K2 ⟨FW, RF, LB⟩ — are selected to minimize a normalized delay-load cost while satisfying resource and SLA constraints. Security upgrades are immediate; downgrades are stabilized by a hysteresis holding interval (τH = 10 s).

---

## Repository Structure

```
├── simulation/
│   ├── simulator.py              # Core discrete-event simulator
│   │                             #   NSFNET topology, VNF placement, SFC admission,
│   │                             #   reconfiguration, hysteresis, profile-transition logging
│   ├── run_experiments.py        # Full experiment runner (static + reconfiguration)
│   ├── generate_figures.py       # Reproduces all paper figures (Figs 1–6) and LaTeX tables
│   ├── gen_arch_fig.py           # Architecture diagram generator (Fig 1 — legacy)
│   └── validate_hysteresis.py    # Standalone hysteresis validation script
├── results/
│   ├── results.json              # All measured experiment outputs
│   │                             #   - static: 4 methods × 5 η × 11 req rates
│   │                             #   - reconfig: Trace A & B × 4 methods
│   │                             #   - transition_timestamps per run (for hysteresis validation)
│   │                             #   - profile_trace per second (for timeline plots)
│   │                             #   - params: all configuration values
│   └── figures/
│       ├── fig1_admission_rate.{png,pdf}
│       ├── fig2_throughput.{png,pdf}
│       ├── fig3_delay.{png,pdf}
│       ├── fig4_utilization.{png,pdf}
│       ├── fig5_saturation.{png,pdf}
│       ├── fig6_reconfig.{png,pdf}
│       ├── fig_architecture.{png,pdf}   # IEEE-format architecture figure
│       ├── table1_admission.tex
│       ├── table2_utilization.tex
│       └── table3_reconfig.tex
└── paper/
    └── Project7_AttackAware_AALB.docx   # Full IEEE-format paper (source)
```

---

## Simulation Parameters

| Parameter | Value |
|---|---|
| Topology | NSFNET — 14 nodes, 21 bidirectional links |
| Node CPU capacity | 1 core per node |
| Node memory capacity | 1024 MB per node |
| Link capacity | 100 Mbps |
| Link propagation delay | 2 ms |
| Request arrival rate ν | {50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800} req/s |
| Attack ratio η | {0.0, 0.2, 0.4, 0.7, 0.8} |
| Attack thresholds | τ₁ = 0.30, τ₂ = 0.60 |
| Hysteresis holding interval | τH = 10 s |
| Cost weight | α = 0.6 |
| Run duration (static) | 120 s × 3 independent runs |
| Run duration (reconfig) | 120 s × 5 independent runs |

### Security Profiles

| Profile | VNF Chain | VNFs | Total Processing Delay |
|---|---|---|---|
| K0 | ⟨LB⟩ | cpu=0.10, mem=128 MB, 1 ms | 1 ms |
| K1 | ⟨RF, LB⟩ | RF: cpu=0.15, mem=128 MB, 2 ms | 3 ms |
| K2 | ⟨FW, RF, LB⟩ | FW: cpu=0.20, mem=192 MB, 3 ms | 6 ms |

K0 provides **no attack filtering**. Only K1 and K2 can identify and discard attack traffic.

### Comparison Methods

| Method | Profile | Placement |
|---|---|---|
| RR-SFC | Static K2 (always) | Round-robin |
| LC-SFC | Static K2 (always) | Least-loaded |
| Original AALB | Adaptive, K1 minimum | Min-cost feasible |
| **AALB (proposed)** | **Adaptive K0/K1/K2** | **Min-cost feasible** |

---

## Reproducing the Experiments

### Prerequisites

```bash
pip install -r requirements.txt
# numpy>=1.24, matplotlib>=3.7
```

### Step 1 — Run all experiments

```bash
python simulation/run_experiments.py
```

This runs all static experiments (4 methods × 5 η × 11 req rates × 3 runs) and both
reconfiguration traces (Trace A: mild; Trace B: severe) for all 4 methods × 5 runs each.
Results are written to `results/results.json` with checkpointing after each η stripe
(safe to interrupt and resume).

Expected runtime: 15–30 minutes on a modern laptop.

### Step 2 — Validate hysteresis

```bash
python simulation/validate_hysteresis.py
```

Reads `results/results.json` and verifies that every recorded downgrade occurred only
after the lower attack state had persisted continuously for ≥ τH = 10 s (eq. 9 of the
paper). Prints a full gap table for both traces and exits 0 on pass, 1 on violation.

Expected output (confirming the paper's claim):
```
OVERALL: PASSED — all downgrades respect τH = 10 s holding interval
```

### Step 3 — Regenerate all figures

```bash
python simulation/generate_figures.py
```

Reads `results/results.json` and writes all six paper figures (PNG + PDF) and three
LaTeX tables to `results/figures/`.

---

## Key Results (from `results/results.json`)

- **35.7% lower mean end-to-end delay** vs. static K2 baselines under benign traffic (η = 0.0)
- **44.4% lower CPU utilization** vs. RR-SFC at moderate attack pressure (η = 0.4, ν = 150 req/s)
- **Full legitimate admission** sustained through 500 req/s at η = 0.4 before saturation
- **Hysteresis validation**: all downgrades ≥ 25 s after preceding upgrade (τH = 10 s minimum hold confirmed)
- **Reconfiguration counts**:
  - Trace A (mild): 93.2 upgrades / 57.2 downgrades / 4.0 blocked per 120 s run
  - Trace B (severe): 38.2 upgrades / 103.0 downgrades / 5.8 blocked per 120 s run

---

## Data Availability

All simulation code, experiment configuration, result data, and figure-generation
scripts are in this repository. The complete `results/results.json` file (pre-computed)
is included so figures can be regenerated without re-running experiments.

Profile-transition timestamps and per-second profile traces are embedded in
`results/results.json` under `results['reconfig']['trace_a']['aalb']['transition_timestamps']`
and `results['reconfig']['trace_a']['aalb']['profile_trace']` respectively, enabling
independent verification of the hysteresis behavior reported in Section V-G.
