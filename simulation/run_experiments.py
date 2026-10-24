"""
Run all experiments for Project 7 and save results to JSON.
NET 470 — Attack-Aware Adaptive Security Service Orchestration
"""
import json
import os
import sys

# Add simulation directory to path (robust — no hardcoded scratchpad paths)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulator import (
    Simulator, NSFNET_NODES, NSFNET_EDGES,
    compute_eta, compute_attack_state
)

METHODS = ['aalb', 'rr_sfc', 'lc_sfc', 'original_aalb']
METHOD_LABELS = {
    'aalb':          'AALB (proposed)',
    'rr_sfc':        'RR-SFC',
    'lc_sfc':        'LC-SFC',
    'original_aalb': 'Original AALB',
}

# Output path (save incrementally)
out_path = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'results.json'))
os.makedirs(os.path.dirname(out_path), exist_ok=True)

def save_checkpoint(data):
    """Save results to JSON, converting numeric keys to strings."""
    def stringify_keys(d):
        if isinstance(d, dict):
            return {str(k): stringify_keys(v) for k, v in d.items()}
        if isinstance(d, list):
            return [stringify_keys(v) for v in d]
        return d
    with open(out_path, 'w') as f:
        json.dump(stringify_keys(data), f, indent=2)

# ─── Experiment 1: Static ────────────────────────────────────────────────────
# Vary request rate and attack ratio.
# Extended range to find saturation point (system degrades under heavy load).
#
# REQ_RATES extended to 800 req/s so we can observe where admission rate
# drops, delay climbs, or throughput saturates / degrades — the "knee" of
# the performance curve that the professor asked for.

REQ_RATES     = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800]
ATTACK_ETAS   = [0.0, 0.2, 0.4, 0.7, 0.8]   # attack ratio η
LAMBDA_L_BASE = 500.0    # baseline legitimate monitor events/s (used for compute_eta)

DURATION_STATIC = 120.0
N_RUNS_STATIC   = 3   # 3 runs per config balances variance vs. speed

print("=== Experiment 1: Static ===")
print(f"Rates: {REQ_RATES}")
print(f"Attack ratios: {ATTACK_ETAS}")
static_results = {}

for method in METHODS:
    static_results[method] = {}
    for eta in ATTACK_ETAS:
        static_results[method][eta] = {}
        lambda_L = LAMBDA_L_BASE * (1 - eta)
        lambda_A = LAMBDA_L_BASE * eta
        for req_rate in REQ_RATES:
            print(f"  {method:<16} η={eta:.1f}  rate={req_rate:>4} req/s ...", end=' ', flush=True)
            sim = Simulator(NSFNET_NODES, NSFNET_EDGES, method, rng_seed=42)
            res = sim.run_static(
                DURATION_STATIC,
                req_rate=req_rate,
                lambda_L=lambda_L,
                lambda_A=lambda_A,
                n_runs=N_RUNS_STATIC
            )
            static_results[method][eta][req_rate] = res
            print(
                f"admission={res['admission_rate']:.3f}  "
                f"throughput={res['throughput']:.1f}  "
                f"delay={res['mean_delay']:.2f}ms  "
                f"cpu={res['util_cpu']:.2f}  bw={res['util_bw']:.2f}"
            )
        # Save after each (method, eta) stripe — so partial runs are usable
        save_checkpoint({'static': static_results, 'reconfig': {}, 'params': {
            'req_rates': REQ_RATES, 'attack_etas': ATTACK_ETAS,
            'duration_static': DURATION_STATIC, 'n_runs_static': N_RUNS_STATIC,
        }})
        print(f"  [checkpoint saved for {method} η={eta:.1f}]")

# ─── Experiment 2: Reconfiguration ───────────────────────────────────────────
RECONFIG_TRACE_A = [
    (0,   0.0), (15,  0.4), (30,  0.2), (45,  0.0),
    (60,  0.4), (75,  0.2), (90,  0.0), (105, 0.4),
]
RECONFIG_TRACE_B = [
    (0,   0.0), (15,  0.7), (30,  0.4), (45,  0.0),
    (60,  0.8), (75,  0.4), (90,  0.2), (105, 0.0),
]

DURATION_RECONFIG = 120.0
N_RUNS_RECONFIG   = 5

print("\n=== Experiment 2: Reconfiguration ===")
reconfig_results = {}

for trace_name, trace in [('trace_a', RECONFIG_TRACE_A), ('trace_b', RECONFIG_TRACE_B)]:
    reconfig_results[trace_name] = {}
    for method in METHODS:
        print(f"  {method:<16} {trace_name} ...", end=' ', flush=True)
        sim = Simulator(NSFNET_NODES, NSFNET_EDGES, method, rng_seed=42)
        res = sim.run_reconfig(
            DURATION_RECONFIG,
            req_rate=0.5,
            attack_trace=trace,
            n_runs=N_RUNS_RECONFIG
        )
        reconfig_results[trace_name][method] = res
        print(
            f"upgrades={res['upgrades']:.1f}  "
            f"downgrades={res['downgrades']:.1f}  "
            f"blocked={res['blocked']:.1f}"
        )

# ─── Final save ───────────────────────────────────────────────────────────────
results = {
    'static':   static_results,
    'reconfig': reconfig_results,
    'params': {
        'req_rates':          REQ_RATES,
        'attack_etas':        ATTACK_ETAS,
        'duration_static':    DURATION_STATIC,
        'n_runs_static':      N_RUNS_STATIC,
        'duration_reconfig':  DURATION_RECONFIG,
        'n_runs_reconfig':    N_RUNS_RECONFIG,
        'reconfig_trace_a':   RECONFIG_TRACE_A,
        'reconfig_trace_b':   RECONFIG_TRACE_B,
    }
}
save_checkpoint(results)
print(f"\nResults saved to {out_path}")

# ─── Summary tables ───────────────────────────────────────────────────────────
print("\n=== Summary: Legitimate Admission Rate by Method and η (rate=150 req/s) ===")
print(f"{'Method':<22}", end='')
for eta in ATTACK_ETAS:
    print(f"  η={eta:.1f}", end='')
print()
for method in METHODS:
    print(f"{METHOD_LABELS[method]:<22}", end='')
    for eta in ATTACK_ETAS:
        ar = static_results[method][eta].get(150, {}).get('admission_rate', 0)
        print(f"  {ar:.3f}", end='')
    print()

print("\n=== Summary: Legitimate Throughput (req/s) at rate=150 req/s ===")
print(f"{'Method':<22}", end='')
for eta in ATTACK_ETAS:
    print(f"   η={eta:.1f}", end='')
print()
for method in METHODS:
    print(f"{METHOD_LABELS[method]:<22}", end='')
    for eta in ATTACK_ETAS:
        tp = static_results[method][eta].get(150, {}).get('throughput', 0)
        print(f"  {tp:6.2f}", end='')
    print()

print("\n=== Summary: Mean E2E Delay (ms) at rate=150 req/s ===")
print(f"{'Method':<22}", end='')
for eta in ATTACK_ETAS:
    print(f"   η={eta:.1f}", end='')
print()
for method in METHODS:
    print(f"{METHOD_LABELS[method]:<22}", end='')
    for eta in ATTACK_ETAS:
        d = static_results[method][eta].get(150, {}).get('mean_delay', 0)
        print(f"  {d:6.2f}", end='')
    print()

print("\n=== Summary: Average CPU Utilization at rate=150 req/s (η=0.4) ===")
for method in METHODS:
    cpu = static_results[method][0.4].get(150, {}).get('util_cpu', 0)
    bw  = static_results[method][0.4].get(150, {}).get('util_bw', 0)
    print(f"  {METHOD_LABELS[method]:<22}  cpu={cpu:.3f}  bw={bw:.3f}")

print("\n=== Saturation: AALB admission_rate vs rate (η=0.4) ===")
for req_rate in REQ_RATES:
    ar = static_results['aalb'][0.4].get(req_rate, {}).get('admission_rate', 0)
    tp = static_results['aalb'][0.4].get(req_rate, {}).get('throughput', 0)
    print(f"  rate={req_rate:>4}  admission={ar:.3f}  throughput={tp:.1f}")
