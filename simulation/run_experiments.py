"""
Run all experiments for Project 7 and save results to JSON.
"""
import json
import sys
sys.path.insert(0, '/tmp/claude-0/-home-claude/8641c8f6-757f-517a-9271-1fc015db3b24/scratchpad')

from simulator import (
    Simulator, NSFNET_NODES, NSFNET_EDGES,
    compute_eta, compute_attack_state
)

METHODS = ['aalb', 'rr_sfc', 'lc_sfc', 'original_aalb']
METHOD_LABELS = {
    'aalb':         'AALB (proposed)',
    'rr_sfc':       'RR-SFC',
    'lc_sfc':       'LC-SFC',
    'original_aalb':'Original AALB',
}

# ─── Experiment 1: Static ────────────────────────────────────────────────────
# Vary request rate (50–250 req/s) and attack ratio (0, 0.2, 0.4, 0.7, 0.8)
# For each combination, measure: success_rate, mean_delay, p95_delay, throughput

REQ_RATES    = [50, 100, 150, 200, 250]   # req/s
ATTACK_ETAS  = [0.0, 0.2, 0.4, 0.7, 0.8] # attack ratio η
LAMBDA_L_BASE = 500.0  # legitimate monitor events/s

DURATION_STATIC = 120.0
N_RUNS_STATIC   = 10

print("=== Experiment 1: Static ===")
static_results = {}

for method in METHODS:
    static_results[method] = {}
    for eta in ATTACK_ETAS:
        static_results[method][eta] = {}
        lambda_L = LAMBDA_L_BASE * (1 - eta)
        lambda_A = LAMBDA_L_BASE * eta
        for req_rate in REQ_RATES:
            print(f"  {method} η={eta:.1f} rate={req_rate}...", end=' ', flush=True)
            sim = Simulator(NSFNET_NODES, NSFNET_EDGES, method, rng_seed=42)
            res = sim.run_static(
                DURATION_STATIC, req_rate / DURATION_STATIC,
                lambda_L, lambda_A, n_runs=N_RUNS_STATIC
            )
            static_results[method][eta][req_rate] = res
            print(f"sr={res['success_rate']:.3f} delay={res['mean_delay']:.2f}ms")

# ─── Experiment 2: Reconfiguration ───────────────────────────────────────────
# Long-lived requests, time-varying attack trace: 0→0.4→0.2→0 (15s/state)
# and the harder trace with 0.7/0.8

RECONFIG_TRACE_A = [
    (0,    0.0),
    (15,   0.4),
    (30,   0.2),
    (45,   0.0),
    (60,   0.4),
    (75,   0.2),
    (90,   0.0),
    (105,  0.4),
]

RECONFIG_TRACE_B = [
    (0,    0.0),
    (15,   0.7),
    (30,   0.4),
    (45,   0.0),
    (60,   0.8),
    (75,   0.4),
    (90,   0.2),
    (105,  0.0),
]

DURATION_RECONFIG = 120.0
N_RUNS_RECONFIG   = 5

print("\n=== Experiment 2: Reconfiguration ===")
reconfig_results = {}

for trace_name, trace in [('trace_a', RECONFIG_TRACE_A), ('trace_b', RECONFIG_TRACE_B)]:
    reconfig_results[trace_name] = {}
    for method in METHODS:
        print(f"  {method} {trace_name}...", end=' ', flush=True)
        sim = Simulator(NSFNET_NODES, NSFNET_EDGES, method, rng_seed=42)
        res = sim.run_reconfig(
            DURATION_RECONFIG, req_rate=0.5,
            attack_trace=trace, n_runs=N_RUNS_RECONFIG
        )
        reconfig_results[trace_name][method] = res
        print(f"up={res['upgrades']:.1f} dn={res['downgrades']:.1f}")

# ─── Save results ─────────────────────────────────────────────────────────────

results = {
    'static':  static_results,
    'reconfig': reconfig_results,
    'params': {
        'req_rates':   REQ_RATES,
        'attack_etas': ATTACK_ETAS,
        'duration_static': DURATION_STATIC,
        'n_runs_static':   N_RUNS_STATIC,
        'duration_reconfig': DURATION_RECONFIG,
        'n_runs_reconfig':   N_RUNS_RECONFIG,
    }
}

# JSON can't have float keys — stringify them
def stringify_keys(d):
    if isinstance(d, dict):
        return {str(k): stringify_keys(v) for k, v in d.items()}
    return d

with open('/tmp/claude-0/-home-claude/8641c8f6-757f-517a-9271-1fc015db3b24/scratchpad/results.json', 'w') as f:
    json.dump(stringify_keys(results), f, indent=2)

print("\nResults saved to results.json")

# Print summary table
print("\n=== Summary: Success Rate by Method and Attack Ratio (rate=150 req/s) ===")
print(f"{'Method':<20}", end='')
for eta in ATTACK_ETAS:
    print(f"  η={eta:.1f}", end='')
print()
for method in METHODS:
    print(f"{METHOD_LABELS[method]:<20}", end='')
    for eta in ATTACK_ETAS:
        sr = static_results[method][eta][150]['success_rate']
        print(f"  {sr:.3f}", end='')
    print()

print("\n=== Summary: Mean Delay (ms) at rate=150 req/s ===")
print(f"{'Method':<20}", end='')
for eta in ATTACK_ETAS:
    print(f"  η={eta:.1f}", end='')
print()
for method in METHODS:
    print(f"{METHOD_LABELS[method]:<20}", end='')
    for eta in ATTACK_ETAS:
        d = static_results[method][eta][150]['mean_delay']
        print(f"  {d:5.2f}", end='')
    print()
