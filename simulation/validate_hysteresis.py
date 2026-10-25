"""
Hysteresis Validation Script
=============================
Verifies that every downgrade recorded in results.json occurred only after
the lower attack state had persisted continuously for at least τH = 10 s,
as stated in Section IV-F of the paper (eq. 9).

Usage:
    python simulation/validate_hysteresis.py

The script reads results/results.json and checks both reconfiguration traces
(Trace A — mild; Trace B — severe). For each trace it reconstructs the
attack-state timeline and confirms that the time elapsed since the most
recent upgrade before each downgrade is >= τH.

Exit codes:
    0  all checks passed
    1  one or more violations found
"""

import json
import os
import sys

TAU_H = 10.0   # hysteresis holding interval (seconds), matches simulator

results_path = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'results.json'))

with open(results_path) as f:
    results = json.load(f)

params = results['params']
TRACE_A = params['reconfig_trace_a']   # [[t, eta], ...]
TRACE_B = params['reconfig_trace_b']

TRACES = {'trace_a (mild)': TRACE_A, 'trace_b (severe)': TRACE_B}

violations = []

print(f"Hysteresis validation  (τH = {TAU_H} s)\n{'='*52}")

for trace_label, trace in TRACES.items():
    aalb = results['reconfig'][trace_label.split()[0]]['aalb']
    timestamps = aalb['transition_timestamps']  # [t, from_k, to_k, reason]
    profile_trace = aalb.get('profile_trace', [])

    upgrades   = [(t, fk, tk) for t, fk, tk, reason in timestamps if reason == 'upgrade']
    downgrades = [(t, fk, tk) for t, fk, tk, reason in timestamps if reason == 'downgrade']

    upgrade_times   = sorted(set(t for t, _, _ in upgrades))
    downgrade_times = sorted(set(t for t, _, _ in downgrades))

    print(f"\n{trace_label}")
    print(f"  Attack trace: {trace}")
    print(f"  Upgrades   at t = {upgrade_times}")
    print(f"  Downgrades at t = {downgrade_times}")

    print(f"\n  Downgrade gap check (must be >= {TAU_H} s after last preceding upgrade):")
    all_ok = True
    for dt, dfrom, dto in sorted(set((t, fk, tk) for t, fk, tk in downgrades)):
        # find the most recent upgrade strictly before dt
        preceding = [ut for ut in upgrade_times if ut < dt]
        if not preceding:
            print(f"    t={dt:6.1f}  K{dfrom}→K{dto}  no preceding upgrade  [SKIP — initial state]")
            continue
        last_up = max(preceding)
        gap = dt - last_up
        status = "✓" if gap >= TAU_H else "✗ VIOLATION"
        if gap < TAU_H:
            all_ok = False
            violations.append(f"{trace_label}: downgrade at t={dt} only {gap}s after upgrade at t={last_up}")
        print(f"    t={dt:6.1f}  K{dfrom}→K{dto}  last upgrade t={last_up:5.1f}  gap={gap:5.1f}s  {status}")

    print(f"\n  {'PASSED ✓' if all_ok else 'FAILED ✗'}")

    print(f"\n  Mean reconfiguration counts (averaged over runs):")
    print(f"    Upgrades : {aalb['upgrades']:.1f}")
    print(f"    Downgrades: {aalb['downgrades']:.1f}")
    print(f"    Blocked  : {aalb['blocked']:.1f}")

print(f"\n{'='*52}")
if violations:
    print(f"OVERALL: FAILED — {len(violations)} violation(s):")
    for v in violations:
        print(f"  {v}")
    sys.exit(1)
else:
    print("OVERALL: PASSED — all downgrades respect τH = 10 s holding interval")
    sys.exit(0)
