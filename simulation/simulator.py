"""
Attack-Aware Adaptive Security Service Orchestration Simulator
NET 470 — Project 7
NSFNET 14-node, 21-link topology
"""

import random
import math
import json
import csv
from collections import defaultdict
from copy import deepcopy

# ─── Topology ────────────────────────────────────────────────────────────────

NSFNET_EDGES = [
    (1,2),(1,3),(1,4),(2,3),(2,8),(3,6),(4,5),(4,9),
    (5,6),(5,7),(6,13),(6,14),(7,8),(8,11),
    (9,10),(9,12),(10,11),(10,13),(11,12),(11,14),(12,13)
]
NSFNET_NODES = list(range(1, 15))  # 1..14

RING4_EDGES = [(1,2),(2,3),(3,4),(4,1)]
RING4_NODES = [1,2,3,4]

# ─── Parameters ──────────────────────────────────────────────────────────────

CPU_PER_NODE   = 1.0          # cores
MEM_PER_NODE   = 1024.0       # MB
BW_PER_LINK    = 100.0        # Mbps
PROP_DELAY     = 2.0          # ms per link

# VNF resource costs (CPU cores, MB, processing delay ms)
VNF_SPECS = {
    'LB': {'cpu': 0.10, 'mem': 128, 'delay': 1.0},
    'RF': {'cpu': 0.15, 'mem': 128, 'delay': 2.0},
    'FW': {'cpu': 0.20, 'mem': 192, 'delay': 3.0},
}

# Security profiles and their VNF chains
# K0 = LB only (no classifier, no firewall — cannot filter malicious traffic)
# K1 = RF + LB (Random Forest classifier — can detect and filter attacks)
# K2 = FW + RF + LB (Firewall + classifier — strongest protection)
PROFILES = {
    0: ['LB'],
    1: ['RF', 'LB'],
    2: ['FW', 'RF', 'LB'],
}

# Profiles that CAN filter malicious traffic (have RF or FW)
FILTERING_PROFILES = {1, 2}

# Attack state thresholds
TAU1 = 0.30
TAU2 = 0.60

# Cost weight
ALPHA = 0.6

# Holding interval (seconds) — must persist for TAU_H before downgrade
TAU_H = 10.0

# Request parameters
REQ_BW     = 1.0    # Mbps
DELAY_BOUND = 20.0  # ms

# Mean service duration (seconds)
MEAN_SERVICE_DUR = 0.1  # → expovariate(1/0.1) = expovariate(10)

# Monitoring
MON_INTERVAL = 1.0  # s

# ─── Graph utilities ─────────────────────────────────────────────────────────

def build_graph(nodes, edges):
    """Adjacency list + link set."""
    adj = defaultdict(set)
    link_bw   = {}
    link_delay = {}
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
        key = (min(u,v), max(u,v))
        link_bw[key]    = BW_PER_LINK
        link_delay[key] = PROP_DELAY
    return adj, link_bw, link_delay

def shortest_path(adj, src, dst, n_nodes):
    """BFS shortest path (hop count)."""
    if src == dst:
        return [src]
    from collections import deque
    visited = {src}
    queue   = deque([[src]])
    while queue:
        path = queue.popleft()
        node = path[-1]
        for nb in adj[node]:
            if nb not in visited:
                new_path = path + [nb]
                if nb == dst:
                    return new_path
                visited.add(nb)
                queue.append(new_path)
    return None  # no path

def path_delay(path, link_delay):
    """Sum of propagation delays along a path."""
    total = 0.0
    for i in range(len(path)-1):
        key = (min(path[i], path[i+1]), max(path[i], path[i+1]))
        total += link_delay[key]
    return total

def unique_links(path):
    """Set of canonical link keys along a path."""
    links = set()
    for i in range(len(path)-1):
        links.add((min(path[i], path[i+1]), max(path[i], path[i+1])))
    return links

# ─── Resource state ──────────────────────────────────────────────────────────

class FogState:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.adj, self.link_bw_cap, self.link_delay = build_graph(nodes, edges)
        self.cpu_avail  = {n: CPU_PER_NODE  for n in nodes}
        self.mem_avail  = {n: MEM_PER_NODE  for n in nodes}
        self.bw_avail   = {k: v for k, v in self.link_bw_cap.items()}
        # active requests: req_id -> {profile_idx, placement, route_links, release_time}
        self.active = {}
        self.next_req_id = 0
        # Pre-compute all-pairs shortest paths (BFS once; paths are static)
        self._path_cache = {}
        for u in nodes:
            for v in nodes:
                if u != v and (u, v) not in self._path_cache:
                    p = shortest_path(self.adj, u, v, len(nodes))
                    self._path_cache[(u, v)] = p
                    if p is not None:
                        self._path_cache[(v, u)] = list(reversed(p))
        # Pre-compute path delays and link sets for every (src,dst) pair
        self._path_delay = {}
        self._path_links = {}
        for (u, v), p in self._path_cache.items():
            if p is not None:
                self._path_delay[(u, v)] = path_delay(p, self.link_delay)
                self._path_links[(u, v)] = unique_links(p)

    def snapshot_avail(self):
        return (dict(self.cpu_avail), dict(self.mem_avail), dict(self.bw_avail))

    def restore_avail(self, snap):
        self.cpu_avail, self.mem_avail, self.bw_avail = snap

    def release_request(self, req_id):
        info = self.active.pop(req_id, None)
        if info is None:
            return
        # return VNF resources
        for vnf, node in info['placement'].items():
            spec = VNF_SPECS[vnf]
            self.cpu_avail[node] += spec['cpu']
            self.mem_avail[node] += spec['mem']
        # return bandwidth
        for link in info['route_links']:
            self.bw_avail[link] += REQ_BW

    def commit_realization(self, req_id, profile_idx, placement, route_links,
                           release_time, attack_history):
        # if upgrading an existing request, release old resources first
        if req_id in self.active:
            self.release_request(req_id)
        # deduct VNF resources
        for vnf, node in placement.items():
            spec = VNF_SPECS[vnf]
            self.cpu_avail[node] -= spec['cpu']
            self.mem_avail[node] -= spec['mem']
        # deduct bandwidth on unique links
        for link in route_links:
            self.bw_avail[link] -= REQ_BW
        self.active[req_id] = {
            'profile_idx':    profile_idx,
            'placement':      placement,
            'route_links':    route_links,
            'release_time':   release_time,
            'attack_history': attack_history,
        }

    def resource_utilization(self):
        """
        Return average CPU, memory, and bandwidth utilization across all nodes/links.
        Utilization = used / capacity.
        """
        n = len(self.nodes)
        cpu_util = sum(1.0 - self.cpu_avail[nd]/CPU_PER_NODE for nd in self.nodes) / n
        mem_util = sum(1.0 - self.mem_avail[nd]/MEM_PER_NODE for nd in self.nodes) / n
        bw_links = list(self.bw_avail.keys())
        bw_util  = sum(1.0 - self.bw_avail[lk]/BW_PER_LINK for lk in bw_links) / max(1, len(bw_links))
        return {'cpu': cpu_util, 'mem': mem_util, 'bw': bw_util}

# ─── Placement / routing feasibility ─────────────────────────────────────────

def find_realizations(state, profile_idx, src, dst, virtual_release=None,
                      max_results=3):
    """
    Returns list of (placement_dict, ordered_node_path, route_links, end2end_delay).
    virtual_release: (vnf->node, links) to restore before checking (for reconfiguration).
    max_results: cap — only the top-3 greedy candidates are tried.

    Performance redesign: instead of exponential backtracking (O(N^|vnfs|)),
    uses O(|vnfs|*N) greedy heuristics producing up to 3 candidate placements.
    This makes the simulator viable at high load (400-800 req/s on 14 nodes).
    """
    vnfs = PROFILES[profile_idx]
    adj  = state.adj

    # temporary resource snapshot
    snap = state.snapshot_avail()
    if virtual_release:
        old_placement, old_links = virtual_release
        for vnf, node in old_placement.items():
            spec = VNF_SPECS[vnf]
            state.cpu_avail[node] += spec['cpu']
            state.mem_avail[node] += spec['mem']
        for link in old_links:
            state.bw_avail[link] += REQ_BW

    nodes = state.nodes
    # Use precomputed path data from state (avoids repeated BFS)
    _path_cache  = state._path_cache
    _path_delay  = state._path_delay
    _path_links  = state._path_links

    def node_load(n):
        cpu_used = 1.0 - state.cpu_avail[n] / CPU_PER_NODE
        mem_used = 1.0 - state.mem_avail[n] / MEM_PER_NODE
        return (cpu_used + mem_used) / 2.0

    sorted_nodes = sorted(nodes, key=node_load)

    def check_placement(placement):
        """Evaluate a complete placement dict; return tuple or None."""
        vnf_nodes = [placement[v] for v in vnfs]
        full_path_nodes = [src] + vnf_nodes + [dst]
        deduped = [full_path_nodes[0]]
        for n in full_path_nodes[1:]:
            if n != deduped[-1]:
                deduped.append(n)
        total_delay = 0.0
        all_links   = set()
        for i in range(len(deduped)-1):
            s2, d2 = deduped[i], deduped[i+1]
            if s2 == d2:
                continue
            key = (s2, d2)
            if key not in _path_cache or _path_cache[key] is None:
                return None
            total_delay += _path_delay.get(key, 0.0)
            all_links |= _path_links.get(key, set())
        for vnf in vnfs:
            total_delay += VNF_SPECS[vnf]['delay']
        if total_delay > DELAY_BOUND:
            return None
        for link in all_links:
            if state.bw_avail.get(link, 0) < REQ_BW:
                return None
        return (dict(placement), deduped, all_links, total_delay)

    def greedy_placement(prefer_spread=False, anchor=None):
        """
        Greedily assign each VNF to the least-loaded feasible node.
        prefer_spread: try not to reuse the same node.
        anchor: if given, prefer nodes close to this node.
        """
        p = {}
        used = set()
        for vnf in vnfs:
            spec = VNF_SPECS[vnf]
            best = None
            best_score = float('inf')
            for n in sorted_nodes:
                if state.cpu_avail[n] < spec['cpu'] or state.mem_avail[n] < spec['mem']:
                    continue
                score = node_load(n)
                if prefer_spread and n in used:
                    score += 0.5   # penalty but not exclusion
                if best is None or score < best_score:
                    best_score = score
                    best = n
            if best is None:
                return None
            p[vnf] = best
            used.add(best)
        return p

    # Generate up to max_results distinct placements
    candidates = []
    seen = set()

    for spread in [False, True, False]:
        p = greedy_placement(prefer_spread=spread)
        if p is None:
            continue
        key = tuple(sorted(p.items()))
        if key not in seen:
            seen.add(key)
            candidates.append(p)
        if len(candidates) >= max_results:
            break

    results = []
    for p in candidates:
        r = check_placement(p)
        if r is not None:
            results.append(r)

    # restore state
    state.restore_avail(snap)
    return results

def select_best(realizations, state, profile_idx):
    """Pick min cost realization: J = alpha*(delay/bound) + (1-alpha)*max_node_load.
    Always returns a 5-tuple (placement, path, links, delay, cost)."""
    best_cost = float('inf')
    best = None
    for item in realizations:
        if len(item) == 4:
            placement, path, links, delay = item
        else:
            placement, path, links, delay, _ = item
        # compute U_k: max normalized node load after placing these VNFs
        max_load = 0.0
        for n in state.nodes:
            cpu_used = CPU_PER_NODE - state.cpu_avail[n]
            mem_used = MEM_PER_NODE - state.mem_avail[n]
            for vnf, vnode in placement.items():
                if vnode == n:
                    cpu_used += VNF_SPECS[vnf]['cpu']
                    mem_used += VNF_SPECS[vnf]['mem']
            load = 0.5 * (cpu_used/CPU_PER_NODE + mem_used/MEM_PER_NODE)
            if load > max_load:
                max_load = load
        cost = ALPHA * (delay / DELAY_BOUND) + (1 - ALPHA) * max_load
        if cost < best_cost:
            best_cost = cost
            best = (placement, path, links, delay, cost)
    return best

# ─── Attack state ─────────────────────────────────────────────────────────────

def compute_attack_state(eta):
    if eta < TAU1:
        return 0
    elif eta < TAU2:
        return 1
    else:
        return 2

def compute_eta(lambda_L, lambda_A):
    total = lambda_L + lambda_A
    if total <= 0:
        return 0.0
    return lambda_A / total

# ─── Round-robin placement helper ────────────────────────────────────────────

_rr_counter = 0

def rr_placement(vnfs, state):
    """Assign each VNF to nodes in round-robin order (skip infeasible)."""
    global _rr_counter
    placement = {}
    nodes = state.nodes
    for vnf in vnfs:
        spec = VNF_SPECS[vnf]
        assigned = False
        for i in range(len(nodes)):
            n = nodes[(_rr_counter + i) % len(nodes)]
            if state.cpu_avail[n] >= spec['cpu'] and state.mem_avail[n] >= spec['mem']:
                placement[vnf] = n
                _rr_counter = (_rr_counter + 1) % len(nodes)
                assigned = True
                break
        if not assigned:
            return None
    return placement

def lc_placement(vnfs, state):
    """Assign each VNF to least-loaded node."""
    placement = {}
    for vnf in vnfs:
        spec = VNF_SPECS[vnf]
        best_node = None
        best_load = float('inf')
        for n in state.nodes:
            if state.cpu_avail[n] >= spec['cpu'] and state.mem_avail[n] >= spec['mem']:
                load = (CPU_PER_NODE - state.cpu_avail[n]) / CPU_PER_NODE
                if load < best_load:
                    best_load = load
                    best_node = n
        if best_node is None:
            return None
        placement[vnf] = best_node
        state.cpu_avail[best_node] -= spec['cpu']
        state.mem_avail[best_node] -= spec['mem']
    return placement

# ─── Simulator ────────────────────────────────────────────────────────────────

class Simulator:
    def __init__(self, nodes, edges, method, rng_seed=42):
        self.nodes  = nodes
        self.edges  = edges
        self.method = method   # 'aalb', 'rr_sfc', 'lc_sfc', 'original_aalb'
        self.rng    = random.Random(rng_seed)
        self.state  = FogState(nodes, edges)

        # metrics
        self.admitted   = 0
        self.rejected   = 0
        self.blocked    = 0   # mandatory upgrade impossible
        self.completed  = 0
        self.delays     = []
        self.upgrades   = 0
        self.downgrades = 0
        self.profile_time = {0: 0.0, 1: 0.0, 2: 0.0}
        self.reconfig_counts = []  # per-request reconfig count

        self.t = 0.0

    def reset(self):
        self.__init__(self.nodes, self.edges, self.method)

    def attack_state_at(self, t, eta_trace):
        """eta_trace: list of (time, eta) pairs."""
        eta = 0.0
        for (ts, e) in eta_trace:
            if t >= ts:
                eta = e
        return compute_attack_state(eta), eta

    # ── Algorithm 1: admission ──────────────────────────────────────────────

    def admit_request(self, req_id, src, dst, arrival_t, release_t, a_t):
        """Returns True if admitted."""
        method = self.method
        state  = self.state

        if method == 'aalb':
            # choose minimum feasible profile k >= a_t
            K_plus = [k for k in range(3) if k >= a_t]
            for k in K_plus:
                reals = find_realizations(state, k, src, dst)
                if reals:
                    raw = select_best(reals, state, k)
                    placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
                    state.commit_realization(
                        req_id, k, placement, links, release_t,
                        attack_history=[(arrival_t, a_t)]
                    )
                    self.delays.append(delay)
                    self.admitted += 1
                    return True
            self.rejected += 1
            return False

        elif method in ('rr_sfc', 'lc_sfc'):
            # always use K2
            k = 2
            reals = find_realizations(state, k, src, dst)
            if not reals:
                self.rejected += 1
                return False
            if method == 'rr_sfc':
                raw = reals[0]
                placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
            else:
                raw = select_best(reals, state, k)
                placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
            state.commit_realization(
                req_id, k, placement, links, release_t,
                attack_history=[(arrival_t, a_t)]
            )
            self.delays.append(delay)
            self.admitted += 1
            return True

        elif method == 'original_aalb':
            # fixed K1 (RF + LB) — classify/filter/route analog
            k = 1
            reals = find_realizations(state, k, src, dst)
            if not reals:
                self.rejected += 1
                return False
            raw = select_best(reals, state, k)
            placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
            state.commit_realization(
                req_id, k, placement, links, release_t,
                attack_history=[(arrival_t, a_t)]
            )
            self.delays.append(delay)
            self.admitted += 1
            return True

        self.rejected += 1
        return False

    # ── Algorithm 2: reconfiguration ────────────────────────────────────────

    def reconfigure_request(self, req_id, t, a_t):
        """Returns 'ok', 'blocked', or 'unchanged'."""
        if req_id not in self.state.active:
            return 'unchanged'
        if self.method not in ('aalb',):
            return 'unchanged'  # static methods don't reconfigure

        info    = self.state.active[req_id]
        k_cur   = info['profile_idx']
        history = info['attack_history']
        history.append((t, a_t))
        src = self.nodes[0]
        dst = self.nodes[-1]

        if k_cur < a_t:
            # mandatory upgrade
            K_plus = [k for k in range(3) if k >= a_t]
            old_placement = info['placement']
            old_links     = info['route_links']
            for k in K_plus:
                reals = find_realizations(
                    self.state, k, src, dst,
                    virtual_release=(old_placement, old_links)
                )
                if reals:
                    raw = select_best(reals, self.state, k)
                    placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
                    self.state.commit_realization(
                        req_id, k, placement, links, info['release_time'], history
                    )
                    self.upgrades += 1
                    return 'ok'
            # no feasible upgrade
            self.state.release_request(req_id)
            self.blocked += 1
            return 'blocked'

        else:
            # possible downgrade — only after TAU_H seconds of lower attack state
            elapsed = t - history[0][0]
            if elapsed < TAU_H:
                return 'unchanged'
            # check if lower profile was sufficient throughout last TAU_H seconds
            recent = [(ts, a) for (ts, a) in history if ts >= t - TAU_H]
            if not recent:
                return 'unchanged'
            max_recent_a = max(a for (_, a) in recent)
            Wr = [k for k in range(k_cur) if k >= max_recent_a]
            if not Wr:
                return 'unchanged'
            old_placement = info['placement']
            old_links     = info['route_links']
            for k in Wr:
                reals = find_realizations(
                    self.state, k, src, dst,
                    virtual_release=(old_placement, old_links)
                )
                if reals:
                    raw = select_best(reals, self.state, k)
                    placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
                    self.state.commit_realization(
                        req_id, k, placement, links, info['release_time'], history
                    )
                    self.downgrades += 1
                    return 'ok'
            return 'unchanged'

    # ── Static experiment (varying attack ratio and request rate) ───────────

    def run_static(self, duration, req_rate, lambda_L, lambda_A, n_runs=10):
        """
        Simulate using discrete-event approach.

        FIX 1 (K0 filtering): K0 profile contains only LB — no RF classifier or
        FW firewall. Malicious traffic must NOT be automatically blocked under K0.
        Only profiles in FILTERING_PROFILES (K1, K2) can detect and drop attacks.

        FIX 2 (admission rate formula):
          Legitimate Admission Rate (%) = Admitted Legitimate / Total Legitimate × 100
          NOT: admitted / (admitted + rejected) which conflates attack traffic.

        FIX 3 (throughput formula):
          Legitimate Throughput (req/s) = Completed Legitimate Requests / Duration

        Returns dict of aggregate metrics including resource utilization.
        """
        all_metrics = []
        for run in range(n_runs):
            rng = random.Random(run * 1000 + 42)
            state = FogState(self.nodes, self.edges)

            # Track legitimate and attack traffic separately
            admitted_legit = 0
            rejected_legit = 0   # legit requests denied due to resource congestion
            admitted_attack = 0  # attack packets that slipped through (K0 only)
            blocked_attack = 0   # attack packets filtered by K1/K2
            completed_legit = 0
            delays_legit = []

            # Resource utilization snapshots
            util_samples = []

            req_id = 0

            eta = compute_eta(lambda_L, lambda_A)
            a_t = compute_attack_state(eta)

            # Generate arrivals
            t_arr = 0.0
            events = []
            while t_arr < duration:
                iat = rng.expovariate(req_rate)
                t_arr += iat
                if t_arr >= duration:
                    break
                is_attack = rng.random() < eta
                svc_dur = rng.expovariate(1.0 / MEAN_SERVICE_DUR)
                events.append((t_arr, 'arrive', req_id, is_attack, svc_dur))
                req_id += 1

            events.sort(key=lambda e: e[0])

            pending_releases = []  # (time, req_id, is_attack)
            i = 0
            all_events = list(events)
            next_util_sample = 1.0

            while i < len(all_events):
                ev = all_events[i]
                i += 1
                t = ev[0]

                # process pending releases up to t
                pending_releases.sort()
                for (rel_t, rid, was_attack) in list(pending_releases):
                    if rel_t <= t:
                        state.release_request(rid)
                        if not was_attack:
                            completed_legit += 1
                        pending_releases.remove((rel_t, rid, was_attack))

                # sample resource utilization periodically
                while next_util_sample <= t:
                    util_samples.append(state.resource_utilization())
                    next_util_sample += 1.0

                if ev[1] == 'arrive':
                    _, _, rid, is_attack, svc_dur = ev

                    # ── FIX 1: Profile-aware attack filtering ──────────────
                    # K0 (LB only): no classifier or firewall — attack traffic
                    #   passes through exactly like legitimate traffic.
                    # K1 (RF + LB): RF classifier detects and blocks attacks.
                    # K2 (FW + RF + LB): FW + RF — strongest filtering.
                    #
                    # For AALB: the active profile is determined by a_t.
                    # For RR-SFC / LC-SFC: always use K2 → always filter.
                    # For Original AALB: fixed K1 → always filter.

                    active_profile = a_t  # profile selected by AALB at this a_t

                    can_filter = False
                    if self.method in ('rr_sfc', 'lc_sfc'):
                        can_filter = True   # always K2
                    elif self.method == 'original_aalb':
                        can_filter = True   # always K1
                    elif self.method == 'aalb':
                        # AALB uses profile >= a_t; when a_t=0, uses K0 → no filter
                        can_filter = (active_profile in FILTERING_PROFILES)

                    if is_attack and can_filter:
                        # Attack detected and blocked by the active security profile
                        blocked_attack += 1
                        continue

                    # attempt admission for this request (legit or undetected attack)
                    src = rng.choice(self.nodes)
                    dst = rng.choice([n for n in self.nodes if n != src])
                    release_t = t + max(0.05, svc_dur)

                    ok = self._admit_one(state, rid, src, dst, t, release_t, a_t, rng)
                    if ok[0]:
                        if not is_attack:
                            admitted_legit += 1
                            delays_legit.append(ok[1])
                        else:
                            admitted_attack += 1  # undetected attack under K0
                        pending_releases.append((release_t, rid, is_attack))
                    else:
                        if not is_attack:
                            rejected_legit += 1

            # Final releases
            for (rel_t, rid, was_attack) in pending_releases:
                state.release_request(rid)
                if not was_attack:
                    completed_legit += 1

            # Average resource utilization
            if not util_samples:
                util_samples = [state.resource_utilization()]
            avg_util = {
                'cpu': sum(u['cpu'] for u in util_samples) / len(util_samples),
                'mem': sum(u['mem'] for u in util_samples) / len(util_samples),
                'bw':  sum(u['bw']  for u in util_samples) / len(util_samples),
            }

            # Active requests estimate: N_active ≈ λ_legitimate × mean_service_dur
            lambda_legit = req_rate * (1 - eta)
            n_active_est = lambda_legit * MEAN_SERVICE_DUR

            total_legit = admitted_legit + rejected_legit
            metrics = {
                # FIX 2: Legitimate admission rate = admitted_legit / total_legit
                'admission_rate':  admitted_legit / max(1, total_legit),
                # FIX 3: Legitimate throughput = completed_legit / duration
                'throughput':      completed_legit / duration,
                'mean_delay':      sum(delays_legit)/len(delays_legit) if delays_legit else 0.0,
                'p95_delay':       sorted(delays_legit)[int(0.95*len(delays_legit))] if delays_legit else 0.0,
                'admitted_legit':  admitted_legit,
                'rejected_legit':  rejected_legit,
                'admitted_attack': admitted_attack,
                'blocked_attack':  blocked_attack,
                'n_active_est':    n_active_est,
                'util_cpu':        avg_util['cpu'],
                'util_mem':        avg_util['mem'],
                'util_bw':         avg_util['bw'],
            }
            all_metrics.append(metrics)

        # average over runs
        keys = ['admission_rate', 'throughput', 'mean_delay', 'p95_delay',
                'admitted_legit', 'rejected_legit', 'admitted_attack', 'blocked_attack',
                'n_active_est', 'util_cpu', 'util_mem', 'util_bw']
        result = {}
        for k in keys:
            result[k] = sum(m[k] for m in all_metrics) / len(all_metrics)
        return result

    def _admit_one(self, state, req_id, src, dst, arrival_t, release_t, a_t, rng):
        method = self.method

        if method == 'aalb':
            K_plus = [k for k in range(3) if k >= a_t]
            for k in K_plus:
                reals = find_realizations(state, k, src, dst)
                if reals:
                    raw = select_best(reals, state, k)
                    placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
                    state.commit_realization(req_id, k, placement, links, release_t,
                                             attack_history=[(arrival_t, a_t)])
                    return (True, delay)
            return (False, 0)

        elif method in ('rr_sfc', 'lc_sfc'):
            k = 2
            reals = find_realizations(state, k, src, dst)
            if not reals:
                return (False, 0)
            if method == 'rr_sfc':
                raw = reals[0]
                placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
            else:
                best = select_best(reals, state, k)
                placement, path, links, delay, cost = best
            state.commit_realization(req_id, k, placement, links, release_t,
                                     attack_history=[(arrival_t, a_t)])
            return (True, delay)

        elif method == 'original_aalb':
            k = 1
            reals = find_realizations(state, k, src, dst)
            if not reals:
                return (False, 0)
            raw = select_best(reals, state, k)
            placement, path, links, delay = raw[0], raw[1], raw[2], raw[3]
            state.commit_realization(req_id, k, placement, links, release_t,
                                     attack_history=[(arrival_t, a_t)])
            return (True, delay)

        return (False, 0)

    # ── Reconfiguration experiment ──────────────────────────────────────────

    def run_reconfig(self, duration, req_rate, attack_trace, n_runs=5):
        """
        Long-lived requests with time-varying attack trace.
        attack_trace: list of (start_time, eta_value)

        FIX: Hysteresis — a downgrade only occurs when the lower attack state
        has persisted CONTINUOUSLY for at least TAU_H=10 seconds. Records
        transition timestamps for validation.

        Returns dict with profile time fractions, upgrade/downgrade counts,
        transition timestamps, and per-second profile trace.
        """
        all_metrics = []
        profile_trace_out = None  # save trace from run 0

        for run in range(n_runs):
            rng = random.Random(run * 999 + 7)
            state = FogState(self.nodes, self.edges)

            upgrades = 0; downgrades = 0; blocked_count = 0
            profile_secs = {0: 0.0, 1: 0.0, 2: 0.0}
            reconfig_latencies = []
            transition_timestamps = []  # (time, from_profile, to_profile, reason)

            # Per-second profile trace for Fig 4
            profile_trace = []   # list of {t, eta, a_t, profile, active_requests}

            req_id = 0
            admitted_reqs = {}  # req_id -> {'profile_idx', 'history', 'release_t'}

            # Generate arrivals at lower rate (long-lived)
            t_arr = 0.0
            arrivals = []
            while t_arr < duration:
                iat = rng.expovariate(req_rate)
                t_arr += iat
                if t_arr >= duration:
                    break
                svc_dur = 120.0  # long-lived requests
                arrivals.append((t_arr, req_id, svc_dur))
                req_id += 1

            # Discrete-time simulation at 1s epochs
            dt = 1.0
            arrival_idx = 0
            pending_releases = {}  # req_id -> release_t

            # Track current system-level profile (profile of majority of active reqs)
            current_sys_profile = 0
            # Track how long current attack state has been below current profile
            low_attack_since = None   # time when attack dropped below profile level

            t = 0.0
            while t < duration:
                # current attack state
                eta = 0.0
                for (ts, e) in attack_trace:
                    if t >= ts:
                        eta = e
                a_t = compute_attack_state(eta)

                # admit new arrivals in this interval
                while arrival_idx < len(arrivals) and arrivals[arrival_idx][0] <= t + dt:
                    arr_t, rid, svc_dur = arrivals[arrival_idx]
                    src = rng.choice(self.nodes)
                    dst = rng.choice([n for n in self.nodes if n != src])
                    release_t = arr_t + svc_dur
                    ok = self._admit_one(state, rid, src, dst, arr_t, release_t, a_t, rng)
                    if ok[0]:
                        admitted_reqs[rid] = {
                            'profile_idx': self._get_profile(state, rid),
                            'history': [(arr_t, a_t)],
                            'release_t': release_t,
                        }
                        pending_releases[rid] = release_t
                    arrival_idx += 1

                # release completed requests
                for rid in list(pending_releases.keys()):
                    if pending_releases[rid] <= t:
                        state.release_request(rid)
                        del pending_releases[rid]
                        admitted_reqs.pop(rid, None)

                # reconfigure active requests (aalb only)
                if self.method == 'aalb':
                    for rid in list(admitted_reqs.keys()):
                        if rid not in state.active:
                            continue
                        info = state.active[rid]
                        k_cur = info['profile_idx']
                        history = info['attack_history']
                        history.append((t, a_t))

                        if k_cur < a_t:
                            # mandatory upgrade — immediate
                            K_plus = [k for k in range(3) if k >= a_t]
                            src2 = self.nodes[0]; dst2 = self.nodes[-1]
                            upgraded = False
                            for k in K_plus:
                                reals = find_realizations(
                                    state, k, src2, dst2,
                                    virtual_release=(info['placement'], info['route_links'])
                                )
                                if reals:
                                    raw = select_best(reals, state, k)
                                    pl, ph, lk, dl = raw[0], raw[1], raw[2], raw[3]
                                    old_k = k_cur
                                    state.commit_realization(
                                        rid, k, pl, lk, info['release_time'], history
                                    )
                                    upgrades += 1
                                    reconfig_latencies.append(dl)
                                    transition_timestamps.append(
                                        (t, old_k, k, 'upgrade')
                                    )
                                    upgraded = True
                                    break
                            if not upgraded:
                                state.release_request(rid)
                                blocked_count += 1
                                admitted_reqs.pop(rid, None)
                                pending_releases.pop(rid, None)

                        elif k_cur > a_t:
                            # ── FIX: Hysteresis — downgrade only after TAU_H seconds ──
                            # The lower attack state must have persisted continuously
                            # for at least TAU_H=10s before a downgrade is allowed.
                            # Check that ALL readings in the last TAU_H seconds are <= a_t.
                            recent = [(ts2, a2) for (ts2, a2) in history if ts2 >= t - TAU_H]
                            if not recent:
                                continue
                            # Need TAU_H seconds of history to have accumulated
                            earliest_recent = min(ts2 for (ts2, _) in recent)
                            window_duration = t - earliest_recent
                            if window_duration < TAU_H:
                                continue  # not enough history yet

                            max_recent_a = max(a2 for (_, a2) in recent)
                            if max_recent_a >= k_cur:
                                continue  # attack was high recently — no downgrade

                            Wr = [k for k in range(k_cur) if k >= max_recent_a]
                            src2 = self.nodes[0]; dst2 = self.nodes[-1]
                            for k in Wr:
                                reals = find_realizations(
                                    state, k, src2, dst2,
                                    virtual_release=(info['placement'], info['route_links'])
                                )
                                if reals:
                                    raw = select_best(reals, state, k)
                                    pl, ph, lk, dl = raw[0], raw[1], raw[2], raw[3]
                                    old_k = k_cur
                                    state.commit_realization(
                                        rid, k, pl, lk, info['release_time'], history
                                    )
                                    downgrades += 1
                                    transition_timestamps.append(
                                        (t, old_k, k, 'downgrade')
                                    )
                                    break

                # Determine dominant system profile at this timestep
                if state.active:
                    profiles_active = [info['profile_idx'] for info in state.active.values()]
                    sys_profile = max(profiles_active)  # highest active profile
                else:
                    sys_profile = a_t  # no active requests — use attack state

                # record profile distribution
                for rid, info in state.active.items():
                    k = info['profile_idx']
                    profile_secs[k] += dt

                # Per-second trace for Fig 4
                profile_trace.append({
                    't':               t,
                    'eta':             round(eta, 4),
                    'a_t':             a_t,
                    'profile':         sys_profile,
                    'active_requests': len(state.active),
                })

                t += dt

            total_profile = sum(profile_secs.values()) or 1.0
            metrics = {
                'upgrades':    upgrades,
                'downgrades':  downgrades,
                'blocked':     blocked_count,
                'profile_frac': {k: profile_secs[k]/total_profile for k in range(3)},
                'mean_reconfig_delay': sum(reconfig_latencies)/len(reconfig_latencies) if reconfig_latencies else 0.0,
                'transition_timestamps': transition_timestamps,
            }
            all_metrics.append(metrics)

            if run == 0:
                profile_trace_out = profile_trace

        # average
        result = {
            'upgrades':   sum(m['upgrades'] for m in all_metrics) / len(all_metrics),
            'downgrades': sum(m['downgrades'] for m in all_metrics) / len(all_metrics),
            'blocked':    sum(m['blocked'] for m in all_metrics) / len(all_metrics),
            'profile_frac': {
                k: sum(m['profile_frac'][k] for m in all_metrics) / len(all_metrics)
                for k in range(3)
            },
            'mean_reconfig_delay': sum(m['mean_reconfig_delay'] for m in all_metrics) / len(all_metrics),
            # transition timestamps from run 0 (for Fig 4 validation)
            'transition_timestamps': all_metrics[0]['transition_timestamps'],
            # per-second profile trace from run 0 (for Fig 4)
            'profile_trace': profile_trace_out,
        }
        return result

    def _get_profile(self, state, req_id):
        if req_id in state.active:
            return state.active[req_id]['profile_idx']
        return 0


if __name__ == '__main__':
    print("Simulator module loaded OK.")
    # quick sanity check on 4-node ring
    s = Simulator(RING4_NODES, RING4_EDGES, 'aalb', rng_seed=0)
    r = s.run_static(30.0, req_rate=10.0, lambda_L=100, lambda_A=50, n_runs=2)
    print("4-node ring AALB:", r)
