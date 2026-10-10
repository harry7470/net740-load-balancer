# Attack-Aware Adaptive Security Service Orchestration for DDoS-Resilient Fog Networks

**NET 470 — Project 7**  
Harsh Patel & Nimrah Ashraf — DePaul University, School of Computing

---

## Overview

This repository contains the full simulation implementation and experimental artifacts for the paper:

> *Attack-Aware Adaptive Security Service Orchestration for DDoS-Resilient Fog Networks*

The proposed **AALB (Attack-Aware Load Balancer)** framework dynamically adapts the active security service function chain (SFC) in an NFV-enabled fog network based on real-time DDoS attack-state estimation. Three bounded security profiles — K0 ⟨LB⟩, K1 ⟨RF, LB⟩, K2 ⟨FW, RF, LB⟩ — are selected to minimize cost while satisfying resource and SLA constraints. Upgrades are immediate; downgrades are stabilized by a hysteresis holding interval.

---

## Repository Structure

```
├── simulation/
│   ├── simulator.py          # Core discrete-event simulator (NSFNET topology, VNF placement, SFC admission, reconfiguration)
│   ├── run_experiments.py    # Static and reconfiguration experiment runner
│   ├── generate_figures.py   # Result figure generation (Figs 2–7)
│   └── gen_arch_fig.py       # System architecture diagram (Fig 1)
├── results/
│   └── results.json          # All measured experiment outputs
├── figures/
│   ├── fig0_architecture.png # System architecture
│   ├── fig1_success_rate_vs_rate.png
│   ├── fig2_delay_vs_rate.png
│   ├── fig3_success_rate_vs_eta.png
│   ├── fig4_delay_vs_eta.png
│   ├── fig5_reconfig_counts.png
│   └── fig6_p95_throughput.png
└── paper/
    └── Project7_AttackAware_AALB.docx   # Full IEEE-format paper
```

---

## Simulation Setup

**Topology:** NSFNET — 14 nodes, 21 bidirectional links  
**Node resources:** 1 CPU core, 1024 MB memory per node  
**Link capacity:** 100 Mbps, 2 ms propagation delay  
**Request arrival rate:** ν ∈ {50, 100, 150, 200, 250} req/s  
**Attack ratio:** η* ∈ {0.0, 0.2, 0.4, 0.7, 0.8}  
**Attack thresholds:** τ1 = 0.30, τ2 = 0.60  
**Holding interval:** τH = 10 s  

### Security Profiles

| Profile | Chain | VNF Delay |
|---------|-------|-----------|
| K0 | ⟨LB⟩ | 1 ms |
| K1 | ⟨RF, LB⟩ | 3 ms |
| K2 | ⟨FW, RF, LB⟩ | 6 ms |

### Baselines

| Method | Profile | Placement |
|--------|---------|-----------|
| RR-SFC | Static K2 | Round-robin |
| LC-SFC | Static K2 | Least-loaded |
| Original AALB | Fixed K1 | Least-cost |
| **AALB (proposed)** | **Adaptive K0/K1/K2** | **Min-cost feasible** |

---

## Running the Experiments

```bash
# Install dependencies
pip install numpy matplotlib

# Run all experiments (static + reconfiguration)
python simulation/run_experiments.py

# Generate all figures
python simulation/generate_figures.py

# Generate architecture diagram
python simulation/gen_arch_fig.py
```

Results are written to `results/results.json`. Figures are saved to `figures/`.

---

## Key Results

- AALB reduces mean end-to-end delay by **52.1%** vs. static K2 baselines under benign traffic (η = 0)
- Under severe attack pressure (η = 0.7), AALB reduces delay by **53.8%** vs. RR-SFC
- Hysteresis produces asymmetric reconfig counts: Trace A → 92.8 upgrades / 57.2 downgrades; Trace B → 38.4 upgrades / 104.8 downgrades

---

## Citation

If you use this code, please cite the associated paper (available in `paper/`).
