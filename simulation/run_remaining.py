"""
Complete the missing experiments and merge into results.json.
Run this after run_experiments.py timed out mid-way.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulator import Simulator, NSFNET_NODES, NSFNET_EDGES

out_path = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'results.json'))

with open(out_path) as f:
    results = json.load(f)

def save():
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)

REQ_RATES   = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800]
ATTACK_ETAS = [0.0, 0.2, 0.4, 0.7, 0.8]
LAMBDA_BASE = 500.0
N_RUNS      = 3
DURATION    = 120.0

# ── Fill in missing static results ───────────────────────────────────────────
for method in ['original_aalb']:
    if method not in results['static']:
        results['static'][method] = {}
    for eta in ATTACK_ETAS:
        eta_key = str(eta)
        if eta_key not in results['static'][method]:
            results['static'][method][eta_key] = {}
        stripe = results['static'][method][eta_key]
        missing_rates = [r for r in REQ_RATES if str(r) not in stripe]
        if not missing_rates:
            print(f'{method} eta={eta}: already complete')
            continue
        print(f'Running {method} eta={eta}: {len(missing_rates)} rates ...')
        lambda_L = LAMBDA_BASE * (1 - eta)
        lambda_A = LAMBDA_BASE * eta
        for req_rate in missing_rates:
            print(f"  rate={req_rate:>4} ...", end=' ', flush=True)
            sim = Simulator(NSFNET_NODES, NSFNET_EDGES, method, rng_seed=42)
            res = sim.run_static(DURATION, req_rate=req_rate,
                                 lambda_L=lambda_L, lambda_A=lambda_A, n_runs=N_RUNS)
            stripe[str(req_rate)] = res
            print(f"ar={res['admission_rate']:.3f} tp={res['throughput']:.1f}")
        save()
        print(f'  [checkpoint saved {method} eta={eta}]')

# ── Reconfiguration ───────────────────────────────────────────────────────────
TRACE_A = [(0,0.0),(15,0.4),(30,0.2),(45,0.0),(60,0.4),(75,0.2),(90,0.0),(105,0.4)]
TRACE_B = [(0,0.0),(15,0.7),(30,0.4),(45,0.0),(60,0.8),(75,0.4),(90,0.2),(105,0.0)]
METHODS = ['aalb', 'rr_sfc', 'lc_sfc', 'original_aalb']

if 'reconfig' not in results:
    results['reconfig'] = {}

print('\n=== Reconfiguration ===')
for trace_name, trace in [('trace_a', TRACE_A), ('trace_b', TRACE_B)]:
    if trace_name not in results['reconfig']:
        results['reconfig'][trace_name] = {}
    for method in METHODS:
        if method in results['reconfig'][trace_name]:
            print(f'  {method} {trace_name}: already done')
            continue
        print(f'  {method:<16} {trace_name} ...', end=' ', flush=True)
        sim = Simulator(NSFNET_NODES, NSFNET_EDGES, method, rng_seed=42)
        res = sim.run_reconfig(120.0, req_rate=0.5, attack_trace=trace, n_runs=5)
        results['reconfig'][trace_name][method] = res
        print(f"upgrades={res['upgrades']:.1f}  downgrades={res['downgrades']:.1f}  blocked={res['blocked']:.1f}")
    save()
    print(f'  [checkpoint saved {trace_name}]')

# Update params
results['params'] = {
    'req_rates': REQ_RATES, 'attack_etas': ATTACK_ETAS,
    'duration_static': DURATION, 'n_runs_static': N_RUNS,
    'duration_reconfig': 120.0, 'n_runs_reconfig': 5,
    'reconfig_trace_a': TRACE_A, 'reconfig_trace_b': TRACE_B,
}
save()
print(f'\nAll results saved to {out_path}')
