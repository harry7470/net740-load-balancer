"""
AALB Simulation — Attack-Aware Adaptive Load Balancing
Revised model addressing all 7 points of Prof. Siasi's feedback.
v2: Added per-constraint rejection breakdown (cpu/mem/bw/delay) and lambda_attack reporting.
"""

import numpy as np
import heapq
import math
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — NSFNET TOPOLOGY
# ─────────────────────────────────────────────────────────────────────────────
NSFNET_LINKS = [
    (0,  1,  8), (0,  2, 10), (1,  3,  5), (1,  5, 16), (2,  5,  9),
    (2,  8, 22), (3,  4,  6), (3,  8, 20), (4,  5, 18), (5,  6, 12),
    (5,  9, 17), (6,  7,  4), (6, 10, 14), (7,  9,  6), (8, 10,  8),
    (8, 13, 25), (9, 11,  5), (9, 12, 18), (10, 12, 10), (11, 13,  7),
    (12, 13,  6),
]
NUM_NODES = 14

def _all_pairs_dijkstra():
    g = defaultdict(list)
    for (u, v, d) in NSFNET_LINKS:
        g[u].append((v, d)); g[v].append((u, d))
    dist = [[math.inf]*NUM_NODES for _ in range(NUM_NODES)]
    path = [[[] for _ in range(NUM_NODES)] for _ in range(NUM_NODES)]
    for s in range(NUM_NODES):
        dist[s][s] = 0.0
        prev = {s: None}
        pq = [(0.0, s)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[s][u]: continue
            for (v, ed) in g[u]:
                nd = dist[s][u] + ed
                if nd < dist[s][v]:
                    dist[s][v] = nd; prev[v] = u
                    heapq.heappush(pq, (nd, v))
        for t in range(NUM_NODES):
            if math.isinf(dist[s][t]): continue
            p, cur = [], t
            while cur is not None: p.append(cur); cur = prev.get(cur)
            path[s][t] = list(reversed(p))
    return dist, path

_DIST, _PATH = _all_pairs_dijkstra()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — VNF SPECS
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class VNF:
    name: str
    cpu_per_req: float
    mem_instance: float
    delay_ms: float

VNF_LB = VNF("LB", cpu_per_req=0.10, mem_instance=24.0, delay_ms=1.0)
VNF_RF = VNF("RF", cpu_per_req=0.15, mem_instance=32.0, delay_ms=2.0)
VNF_FW = VNF("FW", cpu_per_req=0.20, mem_instance=48.0, delay_ms=3.0)

PROFILES = {0: [VNF_LB], 1: [VNF_RF, VNF_LB], 2: [VNF_FW, VNF_RF, VNF_LB]}

def chain_cpu(p): return sum(v.cpu_per_req for v in PROFILES[p])
def chain_mem(p): return sum(v.mem_instance for v in PROFILES[p])
def chain_delay(p): return sum(v.delay_ms for v in PROFILES[p])

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — NODE MODEL  CPU~U[0.8,1.2], Mem~U[256,384]MB, BW~U[80,120]Mbps
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class FogNode:
    node_id: int
    cpu_cap: float
    mem_cap: float
    cpu_used: float = 0.0

    @property
    def cpu_util(self): return self.cpu_used / self.cpu_cap
    def has_mem(self, profile): return chain_mem(profile) <= self.mem_cap
    def has_cpu(self, need): return self.cpu_used + need <= self.cpu_cap

    def queuing_delay(self, mu=50.0):
        rho = min(self.cpu_util, 0.94)
        if rho < 1e-6: return 0.0
        return 1000.0 * rho / (mu * (1.0 - rho))

def make_nodes(rng):
    return [FogNode(i, float(rng.uniform(0.8, 1.2)), float(rng.uniform(256, 384)))
            for i in range(NUM_NODES)]

def make_link_bw(rng):
    return {(min(u,v), max(u,v)): float(rng.uniform(80, 120))
            for (u, v, _) in NSFNET_LINKS}

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — HYSTERESIS CONTROLLER
# ─────────────────────────────────────────────────────────────────────────────
TAU1, TAU2 = 0.30, 0.60

def attack_state(eta): return 0 if eta < TAU1 else (1 if eta < TAU2 else 2)

class HysteresisController:
    def __init__(self, tau_H=10.0):
        self.tau_H = tau_H; self.active = 0
        self.t_last_up = -999.0; self.upgrades = 0; self.downgrades = 0
    def update(self, eta, t):
        a = attack_state(eta); event = None
        if self.active < a:
            self.active = a; self.t_last_up = t; self.upgrades += 1; event = 'upgrade'
        elif self.active > a and (t - self.t_last_up) >= self.tau_H:
            self.active = a; self.downgrades += 1; event = 'downgrade'
        return self.active, event

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — ADMISSION CONTROL  D_max=100ms, BW=0.5Mbps/flow
# Returns (admitted, node, delay, reject_reason)
# reject_reason: 'cpu'|'mem'|'bw'|'delay'  (least-severe binding constraint)
# ─────────────────────────────────────────────────────────────────────────────
D_MAX   = 100.0
ALPHA   = 0.6
REQ_BW  = 0.5

def _bw_ok(path, lbu, lbc):
    for i in range(len(path)-1):
        k = (min(path[i], path[i+1]), max(path[i], path[i+1]))
        if lbc.get(k, 100) - lbu.get(k, 0) < REQ_BW: return False
    return True

def _total_delay(src, vnf, dst, profile, nodes):
    nd = nodes[vnf]
    prop = _DIST[src][vnf] + _DIST[vnf][dst]
    return prop + chain_delay(profile) + nd.queuing_delay()

def _reserve(vnf, profile, path, nodes, lbu):
    nodes[vnf].cpu_used += chain_cpu(profile)
    for i in range(len(path)-1):
        k = (min(path[i], path[i+1]), max(path[i], path[i+1]))
        lbu[k] = lbu.get(k, 0.0) + REQ_BW

def _release(vnf, profile, path, nodes, lbu):
    nodes[vnf].cpu_used = max(0.0, nodes[vnf].cpu_used - chain_cpu(profile))
    for i in range(len(path)-1):
        k = (min(path[i], path[i+1]), max(path[i], path[i+1]))
        lbu[k] = max(0.0, lbu.get(k, 0.0) - REQ_BW)

def _full_path(src, vnf, dst): return _PATH[src][vnf] + _PATH[vnf][dst][1:]

def _reject_reason(saw_cpu, saw_mem, saw_bw, saw_delay):
    # Priority: delay (least severe) > bw > mem > cpu (most severe)
    if saw_delay: return 'delay'
    if saw_bw:    return 'bw'
    if saw_mem:   return 'mem'
    return 'cpu'

def try_admit_cost(src, dst, profile, nodes, lbu, lbc):
    need = chain_cpu(profile); best_J = math.inf; best = None
    saw_cpu = saw_mem = saw_bw = saw_delay = False
    for n in range(NUM_NODES):
        nd = nodes[n]
        if not nd.has_cpu(need):    saw_cpu   = True; continue
        if not nd.has_mem(profile): saw_mem   = True; continue
        path = _full_path(src, n, dst)
        if not _bw_ok(path, lbu, lbc): saw_bw = True; continue
        d = _total_delay(src, n, dst, profile, nodes)
        if d > D_MAX: saw_delay = True; continue
        J = ALPHA*(d/D_MAX) + (1-ALPHA)*(nd.cpu_util + need/nd.cpu_cap)
        if J < best_J: best_J = J; best = (n, d, path)
    if best is None:
        return False, None, 0.0, _reject_reason(saw_cpu, saw_mem, saw_bw, saw_delay)
    n, d, path = best; _reserve(n, profile, path, nodes, lbu)
    return True, n, d, None

def try_admit_rr(src, dst, profile, nodes, lbu, lbc, ctr):
    need = chain_cpu(profile)
    saw_cpu = saw_mem = saw_bw = saw_delay = False
    for _ in range(NUM_NODES):
        n = ctr[0] % NUM_NODES; ctr[0] += 1
        nd = nodes[n]
        if not nd.has_cpu(need):    saw_cpu   = True; continue
        if not nd.has_mem(profile): saw_mem   = True; continue
        path = _full_path(src, n, dst)
        if not _bw_ok(path, lbu, lbc): saw_bw = True; continue
        d = _total_delay(src, n, dst, profile, nodes)
        if d > D_MAX: saw_delay = True; continue
        _reserve(n, profile, path, nodes, lbu)
        return True, n, d, None
    return False, None, 0.0, _reject_reason(saw_cpu, saw_mem, saw_bw, saw_delay)

def try_admit_lc(src, dst, profile, nodes, lbu, lbc):
    need = chain_cpu(profile); best = None; best_load = math.inf
    saw_cpu = saw_mem = saw_bw = saw_delay = False
    for n in range(NUM_NODES):
        nd = nodes[n]
        if not nd.has_cpu(need):    saw_cpu   = True; continue
        if not nd.has_mem(profile): saw_mem   = True; continue
        if nd.cpu_util >= best_load: continue
        path = _full_path(src, n, dst)
        if not _bw_ok(path, lbu, lbc): saw_bw = True; continue
        d = _total_delay(src, n, dst, profile, nodes)
        if d > D_MAX: saw_delay = True; continue
        best = (n, d, path); best_load = nd.cpu_util
    if best is None:
        return False, None, 0.0, _reject_reason(saw_cpu, saw_mem, saw_bw, saw_delay)
    n, d, path = best; _reserve(n, profile, path, nodes, lbu)
    return True, n, d, None

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — SIMULATION CORE
# ─────────────────────────────────────────────────────────────────────────────
SIM_T = 120.0
MU    = 5.0
SEED0 = 42

def run_simulation(lambda_legit, eta_trace, tau_H=10.0, method='AALB',
                   seed=SEED0, sim_T=SIM_T):
    rng = np.random.default_rng(seed)
    nodes = make_nodes(rng); lbc = make_link_bw(rng); lbu = {}

    ctrl = HysteresisController(tau_H)
    if method == 'OrigAALB': ctrl.active = 1; ctrl.tau_H = 1e9

    rr_ctr = [0]

    def get_eta(t):
        e = eta_trace[0][1]
        for tt, ee in eta_trace:
            if t >= tt: e = ee
        return e

    def get_profile(t):
        if method in ('AALB', 'OrigAALB'): return ctrl.active
        return 2

    events = []
    admitted = blocked = 0
    blocked_cpu = blocked_mem = blocked_bw = blocked_delay = 0
    malicious_arrived = 0
    total_delay = 0.0; cpu_snaps = []; reconfig_events = []

    def push_L(t): heapq.heappush(events,
        (t + float(rng.exponential(1.0/lambda_legit)), 'L', None))
    def push_D(t, n, prof, path): heapq.heappush(events,
        (t + float(rng.exponential(1.0/MU)), 'D', (n, prof, path)))

    push_L(0.0)
    for tick in range(1, int(sim_T)+1):
        heapq.heappush(events, (float(tick), 'T', None))

    # Pre-generate malicious arrivals
    t_m = 0.0
    while t_m < sim_T:
        eta0 = get_eta(t_m)
        if eta0 > 0:
            t_m += float(rng.exponential(1.0/(eta0*lambda_legit + 1e-9)))
            if t_m < sim_T:
                heapq.heappush(events, (t_m, 'M', None))
        else:
            break

    while events:
        t, etype, edata = heapq.heappop(events)
        if t > sim_T: break
        eta = get_eta(t)

        if etype == 'T':
            if method == 'AALB':
                old = ctrl.active; new, ev = ctrl.update(eta, t)
                if ev: reconfig_events.append((t, ev, old, new))
            cpu_snaps.append(float(np.mean([nd.cpu_util for nd in nodes])))

        elif etype == 'M':
            malicious_arrived += 1  # dropped immediately, not queued

        elif etype == 'L':
            prof = get_profile(t)
            src = int(rng.integers(0, NUM_NODES))
            dst = int(rng.integers(0, NUM_NODES))
            while dst == src: dst = int(rng.integers(0, NUM_NODES))

            if method == 'RR':
                ok, n, d, reason = try_admit_rr(src, dst, prof, nodes, lbu, lbc, rr_ctr)
            elif method == 'LC':
                ok, n, d, reason = try_admit_lc(src, dst, prof, nodes, lbu, lbc)
            else:
                ok, n, d, reason = try_admit_cost(src, dst, prof, nodes, lbu, lbc)

            if ok:
                admitted += 1; total_delay += d
                push_D(t, n, prof, _full_path(src, n, dst))
            else:
                blocked += 1
                if   reason == 'cpu':   blocked_cpu   += 1
                elif reason == 'mem':   blocked_mem   += 1
                elif reason == 'bw':    blocked_bw    += 1
                elif reason == 'delay': blocked_delay += 1
            push_L(t)

        elif etype == 'D':
            n, prof, path = edata
            _release(n, prof, path, nodes, lbu)

    total = admitted + blocked
    ups = ctrl.upgrades; dns = ctrl.downgrades
    # lambda_attack at mid-simulation (representative point)
    eta_mid = get_eta(sim_T / 2)
    return {
        'method': method,
        'lambda_legit': lambda_legit,
        'lambda_attack': eta_mid * lambda_legit,  # λ_a = η · λ_ℓ at t=T/2
        'tau_H': tau_H,
        'admitted': admitted, 'blocked': blocked,
        'blocked_cpu': blocked_cpu, 'blocked_mem': blocked_mem,
        'blocked_bw': blocked_bw,  'blocked_delay': blocked_delay,
        'malicious_arrived': malicious_arrived,
        'admission_rate': admitted/total if total else 1.0,
        'throughput': admitted/sim_T,
        'mean_delay_ms': total_delay/admitted if admitted else 0.0,
        'mean_cpu_util': float(np.mean(cpu_snaps)) if cpu_snaps else 0.0,
        'upgrades': ups, 'downgrades': dns,
        'total_reconfigs': ups + dns,
        'reconfig_events': reconfig_events,
    }

def avg_res(reps):
    keys = ['admission_rate','throughput','mean_delay_ms','mean_cpu_util',
            'admitted','blocked','blocked_cpu','blocked_mem','blocked_bw','blocked_delay',
            'malicious_arrived','upgrades','downgrades','total_reconfigs']
    out = {k: float(np.mean([r[k] for r in reps])) for k in keys}
    out.update(method=reps[0]['method'], lambda_legit=reps[0]['lambda_legit'],
               tau_H=reps[0]['tau_H'], lambda_attack=reps[0]['lambda_attack'])
    return out

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — EXPERIMENTS
# ─────────────────────────────────────────────────────────────────────────────
LAMBDAS_C    = [50,100,150,200,250,300,350,400,450,500,550,600,700]
LAMBDAS_S    = [350,375,400,425,450,475,500,525,550,575,600,625,650]
METHODS      = ['AALB','RR','LC','OrigAALB']
NR           = 3
NRX          = 5

BENIGN    = [(0, 0.0)]
MOD_ATK   = [(0, 0.4)]
TRACE_A   = [(0,0.0),(20,0.4),(50,0.2),(80,0.0)]
TRACE_B   = [(0,0.0),(15,0.4),(35,0.75),(65,0.35),(90,0.0)]
TRACE_OSC = [(0,0.0),(4,0.4),(8,0.0),(13,0.5),(17,0.1),(22,0.7),(27,0.1),
             (32,0.4),(36,0.0),(41,0.65),(46,0.0),(51,0.4),(56,0.0),
             (62,0.6),(67,0.0),(73,0.35),(78,0.0),(85,0.5),(90,0.0),(96,0.7),(103,0.0)]
TAU_H_VALUES = [0,5,10,20]

def run_all(verbose=True):
    def L(m): verbose and print(m)
    out = {}

    L("Exp A: Admission vs lambda (benign)...")
    out['a'] = {m: [avg_res([run_simulation(lam, BENIGN, 10.0, m, SEED0+r)
                              for r in range(NR)]) for lam in LAMBDAS_C] for m in METHODS}
    L("  done")

    L("Exp B: Throughput/CPU eta=0.4...")
    out['b'] = {m: [avg_res([run_simulation(lam, MOD_ATK, 10.0, m, SEED0+r+100)
                              for r in range(NR)]) for lam in LAMBDAS_C] for m in METHODS}
    L("  done")

    L("Exp C: Delay benign...")
    out['c'] = {m: [avg_res([run_simulation(lam, BENIGN, 10.0, m, SEED0+r+200)
                              for r in range(NR)]) for lam in LAMBDAS_C] for m in METHODS}
    L("  done")

    L("Exp D: Saturation zone...")
    out['d'] = {m: [avg_res([run_simulation(lam, BENIGN, 10.0, m, SEED0+r+300)
                              for r in range(NR)]) for lam in LAMBDAS_S] for m in METHODS}
    L("  done")

    L("Exp E: Reconfiguration traces A and B...")
    out['e'] = {}
    for tn, tr in [('A', TRACE_A), ('B', TRACE_B)]:
        out['e'][tn] = {m: avg_res([run_simulation(300, tr, 10.0, m, SEED0+r+400)
                                     for r in range(NRX)]) for m in METHODS}
        L(f"  Trace {tn} done")

    L("Exp F: Hysteresis sensitivity (TRACE_OSC)...")
    out['f'] = [avg_res([run_simulation(300, TRACE_OSC, float(th), 'AALB', SEED0+r+500)
                          for r in range(NRX)]) for th in TAU_H_VALUES]
    L("  done")

    return out

if __name__ == '__main__':
    import time
    t0 = time.time()
    print("AALB Simulation v2 — running all experiments")
    print("="*68)

    data = run_all(verbose=True)
    ea, eb, ec, ed, ee, ef = data['a'], data['b'], data['c'], data['d'], data['e'], data['f']

    print("\n── ADMISSION RATE @ 600 req/s (benign) ─────────────────────────────")
    for m in METHODS:
        row = min(ea[m], key=lambda r: abs(r['lambda_legit']-600))
        print(f"  {m:12s}: {row['admission_rate']*100:.1f}%")

    print("\n── THROUGHPUT @ 500 req/s (eta=0.4) ────────────────────────────────")
    for m in METHODS:
        row = min(eb[m], key=lambda r: abs(r['lambda_legit']-500))
        print(f"  {m:12s}: {row['throughput']:.1f} req/s  λ_a={row['lambda_attack']:.0f}  CPU={row['mean_cpu_util']*100:.1f}%")

    print("\n── RECONFIG EVENTS ──────────────────────────────────────────────────")
    for tr in ['A','B']:
        print(f"  Trace {tr}:")
        for m in METHODS:
            d = ee[tr][m]
            print(f"    {m:12s}: up={round(d['upgrades'])} dn={round(d['downgrades'])} "
                  f"total={round(d['total_reconfigs'])} SLA={d['admission_rate']*100:.1f}%")

    print("\n── HYSTERESIS TABLE ─────────────────────────────────────────────────")
    print(f"  {'τH':>4}  {'Up':>4}  {'Dn':>4}  {'Total':>5}  {'Admit':>6}")
    for row in ef:
        print(f"  {row['tau_H']:>4.0f}  {round(row['upgrades']):>4}  {round(row['downgrades']):>4}  "
              f"{round(row['total_reconfigs']):>5}  {row['admission_rate']*100:>5.1f}%")

    print("\n── REJECTION BREAKDOWN @ λ=600 (benign, Exp A) ─────────────────────")
    print(f"  {'Method':12s}  {'CPU':>6}  {'Mem':>6}  {'BW':>6}  {'Delay':>6}  {'Total blk':>9}")
    for m in METHODS:
        row = min(ea[m], key=lambda r: abs(r['lambda_legit']-600))
        b = round(row['blocked'])
        bc = round(row['blocked_cpu']); bm = round(row['blocked_mem'])
        bbw = round(row['blocked_bw']); bd = round(row['blocked_delay'])
        print(f"  {m:12s}  {bc:>6}  {bm:>6}  {bbw:>6}  {bd:>6}  {b:>9}")

    def _safe(o):
        if isinstance(o, float) and (math.isnan(o) or math.isinf(o)): return None
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.integer,)):  return int(o)
        if isinstance(o, dict):  return {k: _safe(v) for k, v in o.items()}
        if isinstance(o, list):  return [_safe(v) for v in o]
        return o

    with open('/tmp/aalb_sim/sim_results.json', 'w') as f:
        json.dump(_safe(data), f, indent=2)

    print(f"\nTotal time: {time.time()-t0:.1f}s")
    print("Saved to /tmp/aalb_sim/sim_results.json")
