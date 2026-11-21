"""Auditable, event-driven *simulated* AALB experiments.

Not an observed Docker latency benchmark or a reproduction of a published algorithm.
Security detection is idealized for K1/K2; processing queues are modeled as
non-preemptive FIFO per physical fog node for one probe per admitted session.
The session reservation lifetime is distinct from response/probe latency.
"""
from __future__ import annotations
import hashlib
import heapq
import json
import math
import random
from dataclasses import dataclass, asdict
from collections import defaultdict
from typing import Optional
import aalb_enhanced_handoff_draft as core

METHODS = ('aalb','rr_sfc','lc_sfc','original_aalb')

@dataclass(frozen=True)
class Request:
    id: int
    t: float
    src: int
    dst: int
    is_attack: bool
    session_duration: float


def make_trace(nodes, duration, legitimate_rate, attack_rate, seed):
    """Independently seeded Poisson streams; identical Request objects for every method."""
    if duration <= 0 or legitimate_rate < 0 or attack_rate < 0 or len(nodes) < 2:
        raise ValueError('Invalid duration, rates, or topology')
    requests=[]
    for is_attack, rate, salt in ((False,legitimate_rate,104729),(True,attack_rate,130363)):
        rng=random.Random(seed+salt)
        t=0.0
        if rate <= 0:
            continue
        while True:
            t += rng.expovariate(rate)
            if t >= duration:
                break
            src=rng.choice(nodes)
            dst=rng.choice([n for n in nodes if n!=src])
            lifetime=max(.005,rng.expovariate(1/core.MEAN_SERVICE_DUR))
            requests.append((t,is_attack,src,dst,lifetime))
    requests.sort(key=lambda r:(r[0],r[1],r[2],r[3]))
    return [Request(i,row[0],row[2],row[3],row[1],row[4]) for i,row in enumerate(requests)]


def trace_hash(trace):
    payload=json.dumps([asdict(x) for x in trace],sort_keys=True,separators=(',',':'))
    return hashlib.sha256(payload.encode()).hexdigest()


def attack_level(trace,t):
    level=0
    for ts,eta in trace:
        if ts <= t:
            level=core.compute_attack_state(eta)
        else:
            break
    return level


def queue_probe(state, info, start, server_free):
    """Schedule one FIFO probe through chained VNF servers and network hops.

    Delay is (finish-start)*1000 ms, with propagation, processing, and FIFO
    wait accounted separately. The queue model is a deterministic simulation,
    NOT an OS/HTTP measured latency. No link transmission/serialization delay.
    """
    pos=info['src']; clock=start; prop=proc=wait=0.0
    for vnf in core.PROFILES[info['profile_idx']]:
        node=info['placement'][vnf]
        hops=state._path_cache.get((pos,node), [pos] if pos==node else None)
        if hops is None:
            raise RuntimeError('No path to VNF')
        d=core.path_delay(hops,state.link_delay)/1000
        clock+=d;prop+=d
        ready=max(clock,server_free[node]);wait+=ready-clock
        service=core.VNF_SPECS[vnf]['delay']/1000
        clock=ready+service;proc+=service
        server_free[node]=clock
        pos=node
    hops=state._path_cache.get((pos,info['dst']),[pos] if pos==info['dst'] else None)
    if hops is None:
        raise RuntimeError('No path to destination')
    d=core.path_delay(hops,state.link_delay)/1000
    clock+=d;prop+=d
    return {'response_ms':(clock-start)*1000, 'propagation_ms':prop*1000,
            'processing_ms':proc*1000,'queue_ms':wait*1000,
            'response_at':clock}


def run_one(method, nodes, edges, requests, duration, attack_trace):
    """Run fixed inputs using exact-time event ordering and time-weighted CPU use.

    Events at an equal timestamp: completion, attack-state transition,
    downgrade eligibility, admission. Security upgrades are instantaneous in
    simulated controller time; real controller switching latency is not modeled.
    """
    if method not in METHODS: raise ValueError(method)
    if duration <= 0: raise ValueError('Invalid duration')
    if len({r.id for r in requests})!=len(requests): raise ValueError('Duplicate request ids')
    if any(r.t<0 or r.src not in nodes or r.dst not in nodes or r.src==r.dst
           or r.session_duration<=0 for r in requests): raise ValueError('Invalid request trace')
    ats=sorted(attack_trace)
    if any(not 0<=eta<=1 or ts<0 for ts,eta in ats): raise ValueError('Attack trace invalid')
    sim=core.Simulator(nodes,edges,method)
    state=sim.state
    events=[]
    serial=0
    def push(t,prio,kind,payload):
        nonlocal serial
        if t>duration+1e-10:return
        heapq.heappush(events,(t,prio,serial,kind,payload));serial+=1
    for r in requests:
        if r.t<duration:push(r.t,3,'arrival',r)
    for ts,eta in ats:
        if ts <= duration:push(ts,1,'attack',eta)
    push(duration,4,'end',None)
    active={}
    server_free=defaultdict(float)
    counters=defaultdict(int)
    delay=[]; parts=[]
    last_t=0.0;cpu_integral=0.0; mem_integral=0.0;bw_integral=0.0
    current_level=attack_level(ats,0)
    # event logs enable auditing and targeted scenario checks
    event_log=[]

    def update_time(t):
        nonlocal last_t,cpu_integral,mem_integral,bw_integral
        if t < last_t-1e-8: raise RuntimeError('Nonmonotonic clock')
        u=state.resource_utilization()
        dt=max(0,t-last_t)
        cpu_integral+=dt*u['cpu']; mem_integral+=dt*u['mem'];bw_integral+=dt*u['bw']
        last_t=t

    def end_session(rid,reason,t):
        session=active.pop(rid,None)
        if session is None:return
        state.release_request(rid)
        if reason=='completed':
            counters['completed_total']+=1
            if not session['is_attack']:
                counters['completed_legit']+=1
                if session['compliant']:
                    counters['compliant_completed_legit']+=1
                result=session['probe']
                # A completed session is counted even if its initial probe response
                # is scheduled after its lifetime; in that case its response is
                # canceled, not included in the latency sample.
                if result['response_at']<=t+1e-10:
                    delay.append(result['response_ms']);parts.append(result)
                else:
                    counters['probe_censored_legit']+=1
        elif reason=='security_termination':
            counters['security_terminated']+=1
            if not session['is_attack']:counters['security_terminated_legit']+=1
        event_log.append({'t':t,'event':reason,'id':rid})

    while events:
        t,_,_,kind,payload=heapq.heappop(events)
        update_time(t)
        if kind=='end':break
        if kind=='completion':
            end_session(payload,'completed',t)
        elif kind=='attack':
            new=core.compute_attack_state(payload)
            current_level=new
            for rid,session in list(active.items()):
                if rid not in state.active:continue
                info=state.active[rid]
                prev=info['profile_idx']
                if prev < new:
                    if method=='aalb':
                        counters['upgrade_attempts']+=1
                        chosen=None
                        for k in range(new,3):
                            candidates=core.find_realizations(state,k,info['src'],info['dst'],
                                virtual_release=(info['placement'],info['route_links']))
                            if candidates:
                                chosen=(k,core.select_best(candidates,state,k));break
                        if chosen is None:
                            counters['upgrade_failures']+=1
                            end_session(rid,'security_termination',t)
                            continue
                        k,best=chosen
                        state.commit_realization(rid,k,best[0],best[2],info['release_time'],
                            info['attack_history']+[(t,new)],info['src'],info['dst'])
                        counters['upgrade_successes']+=1
                        # A packet already queued on the old chain is not
                        # magically migrated by an instantaneous controller
                        # change. Mark its session non-compliant until an
                        # explicit in-flight rerouting model is implemented.
                        if session['probe']['response_at']>t+1e-10:
                            counters['inflight_upgrade_overlap']+=1
                            session['compliant']=False
                        event_log.append({'t':t,'event':'upgrade','id':rid,'from':prev,'to':k})
                    else:
                        session['compliant']=False
                elif prev>new and method=='aalb':
                    # New continuously-low interval; stale timers are invalidated
                    session['low_since']=t
                    session['downgrade_token']+=1
                    push(t+core.TAU_H,2,'downgrade',(rid,session['downgrade_token']))
                elif prev<=new:
                    session['low_since']=None
                    session['downgrade_token']+=1
                if rid in state.active and state.active[rid]['profile_idx']<new:
                    session['compliant']=False
        elif kind=='downgrade':
            rid,token=payload
            session=active.get(rid)
            if not session or session['downgrade_token']!=token:continue
            info=state.active[rid]
            if info['profile_idx']<=current_level:continue
            if session['low_since'] is None or t-session['low_since']+1e-10<core.TAU_H:continue
            for k in range(current_level,info['profile_idx']):
                candidates=core.find_realizations(state,k,info['src'],info['dst'],
                    virtual_release=(info['placement'],info['route_links']))
                if candidates:
                    best=core.select_best(candidates,state,k)
                    old=info['profile_idx']
                    state.commit_realization(rid,k,best[0],best[2],info['release_time'],
                        info['attack_history']+[(t,current_level)],info['src'],info['dst'])
                    counters['downgrades']+=1
                    event_log.append({'t':t,'event':'downgrade','id':rid,'from':old,'to':k})
                    break
            session['low_since']=None
        elif kind=='arrival':
            r=payload
            if r.is_attack:counters['generated_attack']+=1
            else:counters['generated_legit']+=1
            # Explicit ideal detector assumption: K1/K2 perfect; K0 no detection
            ideal_protection=2 if method in ('rr_sfc','lc_sfc') else 1 if method=='original_aalb' else current_level
            if r.is_attack and ideal_protection in core.FILTERING_PROFILES:
                counters['filtered_attack']+=1
                continue
            release_t=r.t+r.session_duration
            ok,_=sim._admit_one(state,r.id,r.src,r.dst,r.t,release_t,current_level,sim.rng)
            if not ok:
                counters['rejected_attack' if r.is_attack else 'rejected_legit']+=1
                continue
            info=state.active[r.id]
            session={'is_attack':r.is_attack,'compliant':info['profile_idx']>=current_level,
                     'downgrade_token':0,'low_since':None}
            # Probe queue reservation only once admission/chain placement succeeds.
            session['probe']=queue_probe(state,info,t,server_free)
            # A session cannot complete before its first simulated response.
            release_t=max(release_t,session['probe']['response_at'])
            info['release_time']=release_t
            active[r.id]=session
            counters['admitted_attack' if r.is_attack else 'admitted_legit']+=1
            push(release_t,0,'completion',r.id)
        else:raise RuntimeError(kind)
        # after every event, reservations never exceed physical capacities
        if any(x<-1e-7 for d in (state.cpu_avail,state.mem_avail,state.bw_avail) for x in d.values()):
            raise AssertionError('Negative available resource capacity')
    total=counters['generated_legit']
    measured=len(delay)
    out={
        'method':method,'duration_s':duration,
        'traffic_sha256':trace_hash(requests),
        'generated_legit':total, 'admitted_legit':counters['admitted_legit'],
        'rejected_legit':counters['rejected_legit'],
        'completed_legit':counters['completed_legit'],
        'security_terminated_legit':counters['security_terminated_legit'],
        'security_terminated_total':counters['security_terminated'],
        'completed_total':counters['completed_total'],
        'filtered_attack':counters['filtered_attack'],
        'admitted_attack':counters['admitted_attack'],
        'generated_attack':counters['generated_attack'],
        'upgrade_attempts':counters['upgrade_attempts'] if method=='aalb' else None,
        'upgrade_successes':counters['upgrade_successes'] if method=='aalb' else None,
        'upgrade_failures':counters['upgrade_failures'] if method=='aalb' else None,
        'mandatory_upgrade_success_rate_pct':(100*counters['upgrade_successes']/counters['upgrade_attempts']
            if counters['upgrade_attempts'] else None) if method=='aalb' else None,
        'admission_rate_pct':100*counters['admitted_legit']/total if total else None,
        'completed_throughput_req_s':counters['completed_legit']/duration,
        'security_compliant_completion_rate_pct':(100*counters['compliant_completed_legit']/counters['completed_legit']
            if counters['completed_legit'] else None),
        'security_termination_rate_pct':(100*counters['security_terminated_legit']/counters['admitted_legit']
            if counters['admitted_legit'] else None),
        'mean_e2e_delay_ms':sum(delay)/measured if measured else None,
        'mean_queue_delay_ms':sum(x['queue_ms'] for x in parts)/measured if measured else None,
        'mean_processing_delay_ms':sum(x['processing_ms'] for x in parts)/measured if measured else None,
        'mean_propagation_delay_ms':sum(x['propagation_ms'] for x in parts)/measured if measured else None,
        'latency_sample_size':measured,
        'probe_censored_legit':counters['probe_censored_legit'],
        'inflight_upgrade_overlap':counters['inflight_upgrade_overlap'],
        'sla_violations':sum(x>core.DELAY_BOUND for x in delay),
        'cpu_utilization_pct':100*cpu_integral/duration,
        'memory_utilization_pct':100*mem_integral/duration,
        'bandwidth_utilization_pct':100*bw_integral/duration,
        'incomplete_at_window_end':len(active),
        'incomplete_legit_at_window_end':sum(not session['is_attack'] for session in active.values()),
        'compliant_completed_legit':counters['compliant_completed_legit'],
        'downgrades':counters['downgrades'],
    }
    return out,event_log


def run_matched(methods, nodes, edges, duration, legit_rate, attack_rate, seed, attack_trace):
    reqs=make_trace(nodes,duration,legit_rate,attack_rate,seed)
    results={}
    logs={}
    for method in methods:
        results[method],logs[method]=run_one(method,nodes,edges,reqs,duration,attack_trace)
    if len({x['traffic_sha256'] for x in results.values()})!=1:
        raise AssertionError('Input traces differ')
    return results,logs
