"""Exploratory reproducible AALB experiment runner; outputs unsmoothed raw rows.

Usage: python run_matched_experiments.py --duration 5 --runs 2 --attack-rate 50
Outputs CSV, scenario manifest JSON, and (optional) per-run event logs.
"""
import argparse,csv,json,hashlib
from audit_results import audit
from pathlib import Path
import aalb_enhanced_handoff_draft as core
from aalb_experiment_v2 import run_matched,METHODS

RATES=list(range(100,1001,100))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--duration',type=float,default=5)
    p.add_argument('--runs',type=int,default=2)
    p.add_argument('--attack-rate',type=float,default=50)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--output-dir',default='exploratory_results')
    p.add_argument('--event-logs',action='store_true')
    a=p.parse_args()
    if a.duration<=0 or a.runs<1 or a.attack_rate<0:p.error('Invalid experiment arguments')
    path=Path(a.output_dir);path.mkdir(parents=True,exist_ok=True)
    # These attack-pressure transitions are shared by every method and all loads;
    # eta is an exogenous attack-state *signal*, not derived from injected rate.
    # Agreement on this control-input assumption is needed before publication.
    attack_trace=[(0,0.0),(.25*a.duration,0.4),(.50*a.duration,0.8),(.75*a.duration,0.0)]
    rows=[]; manifests=[]
    for rate in RATES:
        for repetition in range(a.runs):
            seed=a.seed+1000*repetition+rate
            results,logs=run_matched(METHODS,core.NSFNET_NODES,core.NSFNET_EDGES,
                a.duration,rate,a.attack_rate,seed,attack_trace)
            common_hash=next(iter(results.values()))['traffic_sha256']
            manifests.append(dict(legitimate_rate_req_s=rate,run=repetition,seed=seed,
                                  trace_sha256=common_hash, attack_trace=attack_trace))
            for method,result in results.items():
                rows.append(dict(legitimate_rate_req_s=rate,attack_rate_req_s=a.attack_rate,
                                 run=repetition,seed=seed,**result))
                if a.event_logs:
                    (path/f'events_{method}_{rate}_run{repetition}.json').write_text(
                        json.dumps(logs[method],indent=2))
            print(f'rate={rate} run={repetition} common_trace={common_hash[:12]}')
    with (path/'raw_per_run.csv').open('w',newline='') as fp:
        writer=csv.DictWriter(fp,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    (path/'scenario_manifest.json').write_text(json.dumps({
        'status':'exploratory, NOT publication validated',
        'models':'FIFO simulated probe delay, perfect K1/K2 security detection; no controller switching time',
        'topology':'NSFNET14', 'duration_s':a.duration,'runs':a.runs,
        'rates_req_s':RATES,'attack_rate_req_s':a.attack_rate,
        'attack_trace_eta':attack_trace,'methods':list(METHODS),
        'scenario_traces':manifests
    },indent=2))
    audit_result=audit(rows)
    (path/'accounting_audit.json').write_text(json.dumps(audit_result,indent=2))
    print('Created',path/'raw_per_run.csv','scenario_manifest.json, accounting_audit.json')
if __name__=='__main__':main()
