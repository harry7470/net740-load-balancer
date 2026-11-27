# Attack-Aware Adaptive Security Service Orchestration for DDoS-Resilient Fog Networks

**NET 470 / NET 740 — Project 7**

**Authors:** Harsh Patel and Nimrah Ashraf  
**Institution:** DePaul University, School of Computing  
**Course:** Cloud Networking Technologies  
**Date:** November 2026

---

## 1. Project Overview

This project presents an Attack-Aware Adaptive Load Balancing (AALB) framework for security service function chain (SFC) orchestration in network function virtualization (NFV)-enabled fog networks.

The proposed framework dynamically selects security profiles according to changing distributed denial-of-service (DDoS) attack intensity while preserving computational and network resources for legitimate service requests.

The primary objectives are to:

- Improve legitimate request admission under increasing network loads.
- Maintain resource-feasible and delay-aware VNF placement.
- Adapt security profiles according to attack intensity.
- Reduce unnecessary security-profile transitions through hysteresis.
- Preserve security compliance while efficiently utilizing available fog resources.

---

## 2. System Architecture

The proposed architecture consists of:

- Legitimate traffic sources.
- Malicious DDoS traffic sources.
- An ingress fog node with an independent monitoring function.
- A logically centralized AALB controller.
- Distributed NFV-enabled fog nodes.
- A destination service.

The controller evaluates attack intensity, selects an appropriate security profile, and determines feasible VNF placement and traffic routing.

All VNFs belonging to a selected security profile are assigned to a single fog node.

Placement decisions consider:

- CPU availability.
- Memory availability.
- Link bandwidth.
- End-to-end delay constraints.
- Minimum security requirements.

The simulator discards malicious requests at ingress under K1 and K2 profiles before fog-node resource allocation. Under K0 (no attack filter), malicious traffic is admitted alongside legitimate traffic. Consequently, the experiments evaluate legitimate service performance under attack-dependent security requirements.

---

## 3. Security Profiles

| Profile | Attack State | VNF Sequence |
|---|---|---|
| K0 | Low | LB |
| K1 | Moderate | RF → LB |
| K2 | Severe | FW → RF → LB |

### Abbreviations

- LB: Load Balancer
- RF: Rate Filter
- FW: Firewall
- VNF: Virtual Network Function
- NFV: Network Function Virtualization
- SFC: Service Function Chaining
- SLA: Service-Level Agreement

### Security Adaptation

The framework immediately increases the active security profile when stronger protection is required.

Downgrades occur only after the lower attack state persists continuously for the configured hysteresis holding interval.

Existing sessions may be subject to mandatory security upgrades when the active profile changes. Sessions that cannot be upgraded are security-terminated. These behaviors are implemented in `simulation/simulator.py`.

---

## 4. Simulation Parameters

The following parameters correspond to Table I of the research report.

| Parameter | Value |
|---|---|
| Network topology | NSFNET |
| Number of nodes | 14 |
| Number of communication links | 21 |
| Node CPU capacity | Uniform distribution [0.8, 1.2] units |
| Node memory capacity | Uniform distribution [256, 384] MB |
| Link bandwidth | Uniform distribution [80, 120] Mbps |
| Legitimate arrival rate | 100–1,000 requests/s |
| Arrival-rate increment | 100 requests/s |
| Malicious arrival rate | Attack intensity × legitimate arrival rate |
| Load-sweep attack intensity | 0.4 |
| Attack Trace A peak intensity | 0.4 |
| Attack Trace B peak intensity | 0.75 |
| Attack-trace legitimate arrival rate | 300 requests/s |
| Request bandwidth | 0.5 Mbps |
| Simulator service rate | 5 requests/s |
| Delay admission bound | 20 ms |
| Lower attack threshold | 0.30 |
| Upper attack threshold | 0.60 |
| Hysteresis holding intervals | 0, 5, 10, 20 seconds |
| Placement weight (alpha) | 0.6 |
| Load-sweep duration | 30 seconds |
| Attack-trace duration | 120 seconds |
| Random seed | 42 |
| Independent trials | 3 per experimental point |

Legitimate and malicious traffic are generated using independent Poisson arrival processes.

Node and link capacities are sampled at the beginning of each trial and remain fixed throughout that trial.

---

## 5. Security VNF Resource Parameters

The following resource requirements correspond to Table II of the research report.

| VNF | CPU (units) | Memory (MB) | Processing Delay (ms) |
|---|---:|---:|---:|
| LB | 0.10 | 24 | 1 |
| RF | 0.15 | 32 | 2 |
| FW | 0.20 | 48 | 3 |

### Aggregate Security Profile Requirements

| Profile | CPU (units) | Memory (MB) | Processing Delay (ms) |
|---|---:|---:|---:|
| K0 | 0.10 | 24 | 1 |
| K1 | 0.25 | 56 | 3 |
| K2 | 0.45 | 104 | 6 |

---

## 6. Baseline Configurations

Four configurations are evaluated.

| Method | Security Profile | Placement Policy |
|---|---|---|
| AALB (Proposed) | Adaptive K0, K1, K2 | Minimum-cost feasible placement |
| RR-SFC | Fixed K2 | Round-robin placement |
| LC-SFC | Fixed K2 | Least-loaded placement |
| Original AALB | Fixed K1 | Minimum-cost feasible placement |

The proposed AALB framework combines attack-aware security-profile selection with resource- and delay-aware placement.

Comparisons with fixed-K2 methods reflect differences in both security resource requirements and placement policies.

---

## 7. Mathematical Formulation

The controller minimizes a weighted placement cost:

```
J(n,t) = alpha × D(Pn,t)/delta_r
       + (1-alpha) × (rho_n(t) + c_k/C_n)
```

Where:

- n: Candidate fog node.
- t: Current simulation time.
- D(Pn,t): Estimated end-to-end delay.
- delta_r: Request-specific delay bound (20 ms).
- rho_n(t): Current modeled CPU utilization.
- c_k: CPU demand of the selected security profile.
- C_n: Total CPU capacity of the candidate fog node.
- alpha: Relative weighting of delay and CPU load (0.6).

Estimated end-to-end delay consists of:

- Network propagation delay.
- VNF processing delay.
- Estimated queuing delay.

Candidate routes are computed using Dijkstra's shortest-path algorithm.

Only feasible candidates are considered for minimum-cost placement under the proposed admission policy.

---

## 8. Repository Structure

```
net740-load-balancer/
├── simulation/
│   ├── simulator.py              # Core simulation engine (AALB, RR-SFC, LC-SFC, Orig-AALB)
│   ├── run_experiments.py        # Main experiment runner (load sweeps + attack traces)
│   ├── generate_figures.py       # Figure generation script (figs 1–4)
│   ├── generate_figures_v2.py    # Updated figure generation (admission-based throughput label)
│   ├── gen_arch_fig_v4.py        # Architecture diagram generator (final version)
│   └── validate_hysteresis.py    # Hysteresis adaptation validation
├── results/
│   └── results.json              # Experimental results (JSON, keyed by method and rate)
├── figures/                      # Generated figures directory
├── paper/                        # LaTeX source for research report
├── requirements.txt              # Python dependencies
├── README.md                     # This file
└── .gitignore
```

Raw per-run diagnostic data used for security metric figures is located at:

```
results/extended_diagnostic/raw_per_run.csv
```

---

## 9. Installation

### Prerequisites

- Python 3.9 or later (tested with Python 3.13)
- Git
- pip

### Clone the Repository

```bash
git clone https://github.com/harry7470/net740-load-balancer.git
cd net740-load-balancer
```

### Create a Virtual Environment

```bash
python3 -m venv .venv
```

Activate the environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate the environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies: `numpy>=1.24`, `matplotlib>=3.7`

---

## 10. Running the Simulation

Execute the main experiment runner from the repository root:

```bash
python simulation/run_experiments.py
```

This runs load-sweep experiments (λ = 100–1,000 req/s, η = 0.4) across all four evaluated configurations and saves results incrementally to `results/results.json`. The script prints a checkpoint message after each method/rate combination completes.

For the extended diagnostic data used to generate security metric figures, run:

```bash
python simulation/run_remaining.py
```

Output is written to `results/extended_diagnostic/raw_per_run.csv`.

---

## 11. Experimental Methodology

Each experimental point uses three independent trials with random seed 42.

Experiments use controlled random seeds and comparable traffic and resource conditions across the evaluated configurations.

### Load-Sweep Experiments

- Legitimate arrival rates: 100–1,000 requests/s (100 req/s increments).
- Attack intensity: 0.4.
- Simulation duration: 30 seconds.
- Independent trials: 3 per point.

### Dynamic Attack-Trace Experiments

- Legitimate arrival rate: 300 requests/s.
- Trace A peak attack intensity: 0.4.
- Trace B peak attack intensity: 0.75.
- Simulation duration: 120 seconds.
- Default holding interval for trace comparison: 10 seconds.

### Hysteresis Sensitivity

The evaluated holding intervals are:

- 0 seconds.
- 5 seconds.
- 10 seconds.
- 20 seconds.

These experiments evaluate the relationship between security-profile stability and legitimate request admission.

---

## 12. Performance Metrics

### Legitimate Admission Rate

```
Admission Rate (%) =
    Admitted Legitimate Requests /
    Arriving Legitimate Requests × 100
```

### Legitimate Admission-Based Throughput

```
Throughput (requests/s) =
    Admitted Legitimate Requests /
    Simulation Duration (seconds)
```

Admission-based throughput must not be confused with completed-request throughput.

### Mean End-to-End Delay

Mean modeled delay across admitted legitimate requests, expressed in milliseconds.

### CPU Utilization

Time-averaged reserved CPU resources relative to total fog-node CPU capacity.

### Security-Profile Transitions

Total recorded security-profile upgrades and downgrades.

### Additional Security Metrics

- **Security-triggered termination rate:** Percentage of admitted legitimate requests terminated due to a security-profile upgrade.
- **Security-compliant completion rate:** Percentage of admitted legitimate requests that completed under the required security profile.
- **Mandatory security-upgrade success rate (AALB only):** Percentage of mandatory upgrade attempts that succeeded. Baselines (RR-SFC, LC-SFC, Original AALB) operate on fixed profiles and do not perform upgrades; this metric is N/A for those methods.

### Rejection Analysis

Rejected legitimate requests are categorized according to the applicable resource or delay constraint.

---

## 13. Validating Hysteresis

```bash
python simulation/validate_hysteresis.py
```

This confirms that security-profile downgrades occur only after the lower attack state persists for the configured holding interval, consistent with Algorithm 2 of the research report.

---

## 14. Regenerating Experimental Figures

```bash
python simulation/generate_figures_v2.py
```

This regenerates Figures 2–5 (admission rate, throughput, delay, CPU) from `results/results.json`.

To regenerate the architecture diagram:

```bash
python simulation/gen_arch_fig_v4.py
```

Output is written to the `figures/` directory.

### Report Figure Mapping

| Report Figure | Filename | Script |
|---|---|---|
| Figure 1 — System architecture | fig_architecture.pdf | gen_arch_fig_v4.py |
| Figure 2 — Legitimate admission rate | fig1_admission_rate.png | generate_figures_v2.py |
| Figure 3 — Admission-based throughput | fig2_throughput.png | generate_figures_v2.py |
| Figure 4 — End-to-end delay | fig3_delay.png | generate_figures_v2.py |
| Figure 5 — CPU utilization | fig4_cpu.png | generate_figures_v2.py |
| Figure 6 — Security-triggered termination | fig5_security_termination.png | (from raw_per_run.csv) |
| Figure 7 — Security-compliant completion | fig6_compliant_completion.png | (from raw_per_run.csv) |
| Figure 8 — Mandatory upgrade success | fig7_upgrade_success.png | (from raw_per_run.csv) |

Figure numbering is generated automatically by LaTeX and is not embedded in plot titles.

The throughput graph uses admission-based throughput terminology.

The delay graph uses milliseconds and identifies the 20 ms SLA threshold.

---

## 15. Experimental Results

The final experimental results are derived directly from verified simulation outputs.

Reported numerical values are consistent across raw experimental data, generated figures, the research paper, and the project presentation.

### Key Results (λ = 1,000 req/s, η = 0.4)

| Method | Admission Rate | Throughput | Delay | CPU |
|---|---:|---:|---:|---:|
| AALB | 66.0% | 578.8 req/s | 12.2 ms | 75.3% |
| RR-SFC | 25.9% | 249.8 req/s | 21.1 ms | 88.8% |
| LC-SFC | 23.1% | 221.5 req/s | 22.7 ms | 75.2% |
| Original AALB | 51.3% | 497.0 req/s | 16.1 ms | 88.3% |

---

## 16. Reproducibility

To reproduce the reported experiments:

| Item | Value |
|---|---|
| Python version | 3.9 or later (tested on 3.13) |
| numpy | ≥ 1.24 |
| matplotlib | ≥ 3.7 |
| Random seed | 42 |
| Independent trials | 3 per experimental point |
| Results file | results/results.json |
| Raw diagnostic data | results/extended_diagnostic/raw_per_run.csv |

An independent reviewer should be able to:

1. Clone the public repository.
2. Install all required dependencies.
3. Run `python simulation/run_experiments.py`.
4. Run `python simulation/run_remaining.py`.
5. Run `python simulation/generate_figures_v2.py`.
6. Compare the generated figures with those in the final research report.

---

## 17. Data Availability

Repository: https://github.com/harry7470/net740-load-balancer

The repository includes the simulation implementation, experimental data, and figure-generation scripts necessary to reproduce the reported findings.

---

## 18. Academic Context

This project was developed for NET 470 / NET 740:
Cloud Networking Technologies at DePaul University.

Research paper:

Attack-Aware Adaptive Security Service Orchestration
for DDoS-Resilient Fog Networks

Harsh Patel and Nimrah Ashraf  
School of Computing  
DePaul University

November 2026
