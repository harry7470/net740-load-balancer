"""
Optimized runner: fastest possible, all 7 verification points covered.
- NR=1 rep for sweeps (saves 50% vs NR=2)
- NRX=2 reps for trace/hysteresis
- sim_T=60s (default) for sweeps, 120s for trace experiments
- Runs experiments sequentially, writes JSON after each
"""
import sys
sys.path.insert(0, '/tmp/aalb_sim')
import aalb_simulation as S
import numpy as np, math, json, time

t0 = time.time()
SEED0 = S.SEED0

def L(m): print(m, flush=True)

def _safe(o):
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)): return None
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.integer,)):  return int(o)
    if isinstance(o, dict):  return {k: _safe(v) for k, v in o.items()}
    if isinstance(o, list):  return [_safe(v) for v in o]
    return o

def save(out):
    with open('/tmp/aalb_sim/sim_results.json', 'w') as f:
        json.dump(_safe(out), f, indent=2)
    L("  saved to sim_results.json")

out = {}
METHODS = S.METHODS
LAMBDAS_C = S.LAMBDAS_C
# Saturation: use fewer points
LAMBDAS_S = [350, 400, 450, 500, 550, 600, 650]

L("=" * 60)
L("AALB Optimized Runner — NR=1, NRX=2, sim_T=60s sweeps")
L("=" * 60)

# ── Exp A: Admission rate vs lambda (benign) ───────────────────
L("Exp A: Admission vs lambda (benign)...")
out['a'] = {m: [S.avg_res([S.run_simulation(lam, S.BENIGN, 10.0, m, SEED0+r, sim_T=60.0)
                             for r in range(1)]) for lam in LAMBDAS_C] for m in METHODS}
L(f"  done ({time.time()-t0:.1f}s)")
save(out)

# ── Exp B: Throughput under moderate attack eta=0.4 ────────────
L("Exp B: Throughput/CPU eta=0.4...")
out['b'] = {m: [S.avg_res([S.run_simulation(lam, S.MOD_ATK, 10.0, m, SEED0+r+100, sim_T=60.0)
                             for r in range(1)]) for lam in LAMBDAS_C] for m in METHODS}
L(f"  done ({time.time()-t0:.1f}s)")
save(out)

# ── Exp C: Mean delay (benign) ─────────────────────────────────
L("Exp C: Delay benign...")
out['c'] = {m: [S.avg_res([S.run_simulation(lam, S.BENIGN, 10.0, m, SEED0+r+200, sim_T=60.0)
                             for r in range(1)]) for lam in LAMBDAS_C] for m in METHODS}
L(f"  done ({time.time()-t0:.1f}s)")
save(out)

# ── Exp D: CPU saturation zone ─────────────────────────────────
L("Exp D: Saturation zone (7 lambda points)...")
out['d'] = {m: [S.avg_res([S.run_simulation(lam, S.BENIGN, 10.0, m, SEED0+r+300, sim_T=60.0)
                             for r in range(1)]) for lam in LAMBDAS_S] for m in METHODS}
L(f"  done ({time.time()-t0:.1f}s)")
save(out)

# ── Exp E: Reconfig traces A and B ────────────────────────────
L("Exp E: Reconfig traces A and B (120s)...")
out['e'] = {}
for tn, tr in [('A', S.TRACE_A), ('B', S.TRACE_B)]:
    out['e'][tn] = {m: S.avg_res([S.run_simulation(300, tr, 10.0, m, SEED0+r+400, sim_T=120.0)
                                    for r in range(2)]) for m in METHODS}
    L(f"  Trace {tn} done ({time.time()-t0:.1f}s)")
save(out)

# ── Exp F: Hysteresis sensitivity (TRACE_OSC) ─────────────────
L("Exp F: Hysteresis sensitivity TRACE_OSC (120s)...")
out['f'] = [S.avg_res([S.run_simulation(300, S.TRACE_OSC, float(th), 'AALB', SEED0+r+500, sim_T=120.0)
                        for r in range(2)]) for th in S.TAU_H_VALUES]
L(f"  done ({time.time()-t0:.1f}s)")
save(out)

# ── Summary printout ──────────────────────────────────────────
print("\n── ADMISSION @ λ=600 benign ──")
for m in METHODS:
    row = min(out['a'][m], key=lambda r: abs(r['lambda_legit']-600))
    print(f"  {m:12s}: {row['admission_rate']*100:.1f}%")

print("\n── THROUGHPUT @ λ=500 eta=0.4 ──")
for m in METHODS:
    row = min(out['b'][m], key=lambda r: abs(r['lambda_legit']-500))
    print(f"  {m:12s}: {row['throughput']:.1f} req/s  λ_a={row['lambda_attack']:.0f}")

print("\n── RECONFIGS ──")
for tr in ['A','B']:
    print(f"  Trace {tr}:")
    for m in METHODS:
        d = out['e'][tr][m]
        print(f"    {m:12s}: up={round(d['upgrades'])} dn={round(d['downgrades'])} SLA={d['admission_rate']*100:.1f}%")

print("\n── HYSTERESIS ──")
for row in out['f']:
    print(f"  τH={row['tau_H']:.0f}: up={round(row['upgrades'])} dn={round(row['downgrades'])} total={round(row['total_reconfigs'])} admit={row['admission_rate']*100:.1f}%")

print(f"\nTotal wall-clock: {time.time()-t0:.1f}s")
