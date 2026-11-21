"""Fail-closed audit of exploratory per-run output; not research validation.

Example: python audit_results.py exploratory_results/raw_per_run.csv --output exploratory_results/audit.json
"""
import argparse, csv, json, math
from collections import defaultdict
from pathlib import Path

RATES=tuple(range(100,1001,100))
METHODS=('aalb','rr_sfc','lc_sfc','original_aalb')


def number(row,key):
    s=row.get(key,'')
    if s in (None,'','None','null'):return None
    x=float(s)
    if not math.isfinite(x):raise ValueError(f'{key} nonfinite: {s}')
    return x

def count(row,key):
    v=number(row,key)
    if v is None or v < 0 or not v.is_integer():
        raise ValueError(f'{key} invalid count: {v}')
    return int(v)

def approx(got,want,label,tol=1e-5):
    if got is None or not math.isclose(got,want,rel_tol=tol,abs_tol=tol):
        raise ValueError(f'{label}: got={got}, expected={want}')

def audit(rows, expected_methods=METHODS, require_grid=True):
    """Return auditable summary or raise; verify matching inputs and accounting."""
    groups=defaultdict(dict)
    for row in rows:
        rate=count(row,'legitimate_rate_req_s')
        run=count(row,'run')
        method=row['method']
        if method not in expected_methods:raise ValueError(f'Unknown method {method}')
        key=(rate,run)
        if method in groups[key]:raise ValueError(f'Duplicate {key} {method}')
        groups[key][method]=row
        generated=count(row,'generated_legit')
        admitted=count(row,'admitted_legit')
        rejected=count(row,'rejected_legit')
        completed=count(row,'completed_legit')
        terminated=count(row,'security_terminated_legit')
        compliant=count(row,'compliant_completed_legit')
        incomplete=count(row,'incomplete_legit_at_window_end')
        sampled=count(row,'latency_sample_size')
        censored_probe=count(row,'probe_censored_legit')
        if generated != admitted+rejected:raise ValueError(f'{key} admission conservation')
        if admitted != completed+terminated+incomplete:raise ValueError(f'{key} session conservation')
        if compliant > completed:raise ValueError(f'{key} compliant exceeds completed')
        if sampled+censored_probe!=completed:raise ValueError(f'{key} probe accounting')
        duration=number(row,'duration_s')
        if not duration or duration<=0:raise ValueError(f'{key} duration')
        approx(number(row,'admission_rate_pct'),100*admitted/generated if generated else None,'admission rate') if generated else None
        if not generated and number(row,'admission_rate_pct') is not None:raise ValueError('Zero-denominator admission')
        approx(number(row,'completed_throughput_req_s'),completed/duration,'throughput')
        if completed:
            approx(number(row,'security_compliant_completion_rate_pct'),100*compliant/completed,'compliance rate')
        elif number(row,'security_compliant_completion_rate_pct') is not None:
            raise ValueError('Zero-denominator compliance')
        if admitted:
            approx(number(row,'security_termination_rate_pct'),100*terminated/admitted,'security termination rate')
        elif number(row,'security_termination_rate_pct') is not None:
            raise ValueError('Zero-denominator termination')
        for k in ('cpu_utilization_pct','memory_utilization_pct','bandwidth_utilization_pct'):
            n=number(row,k)
            if n is None or n < -1e-7 or n>100+1e-7:raise ValueError(f'{key} {k}: {n}')
        latency=number(row,'mean_e2e_delay_ms')
        components=[number(row,k) for k in ('mean_queue_delay_ms','mean_processing_delay_ms','mean_propagation_delay_ms')]
        if sampled:
            if latency is None or any(x is None for x in components):raise ValueError(f'{key} missing latency')
            approx(latency,sum(components),'latency decomposition')
        elif latency is not None or any(x is not None for x in components):
            raise ValueError(f'{key} zero latency samples with nonnull delay')
        if method=='aalb':
            attempts=count(row,'upgrade_attempts'); success=count(row,'upgrade_successes'); failure=count(row,'upgrade_failures')
            if attempts!=success+failure:raise ValueError(f'{key} upgrade conservation')
            if attempts:approx(number(row,'mandatory_upgrade_success_rate_pct'),100*success/attempts,'upgrade success')
            elif number(row,'mandatory_upgrade_success_rate_pct') is not None:raise ValueError('Zero-attempt upgrade rate')
        elif any(number(row,k) is not None for k in ('upgrade_attempts','upgrade_successes','upgrade_failures','mandatory_upgrade_success_rate_pct')):
            raise ValueError(f'{key} nonadaptive upgrade metrics should be null')
    rates=set(r for r,_ in groups)
    if require_grid and rates != set(RATES):raise ValueError(f'Expected ten x-axis rates; found {sorted(rates)}')
    for (rate,run), methods in groups.items():
        if set(methods)!=set(expected_methods):raise ValueError(f'Missing methods at {rate},run {run}')
        fingerprints={(r['traffic_sha256'],r['seed'],r['duration_s'],r['attack_rate_req_s']) for r in methods.values()}
        if len(fingerprints)!=1:raise ValueError(f'Mismatched scenario inputs at {rate},run {run}')
        if len({count(r,'generated_legit') for r in methods.values()})!=1:raise ValueError('Different legitimate trace length')
        if len({count(r,'generated_attack') for r in methods.values()})!=1:raise ValueError('Different attack trace length')
    # Keep per-run numerical results intact. No smoothing, interpolation, or averaging here.
    return {'status':'accounting-and-input-audit-only; not published-baseline or physical-measurement validation',
            'checked_rows':len(rows),'scenario_count':len(groups),
            'rates_req_s':sorted(rates),'methods':list(expected_methods),'passed':True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('csv_file');p.add_argument('--output');p.add_argument('--allow-partial-grid',action='store_true')
    a=p.parse_args()
    with open(a.csv_file,newline='') as f:rows=list(csv.DictReader(f))
    result=audit(rows,require_grid=not a.allow_partial_grid)
    if a.output:Path(a.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
