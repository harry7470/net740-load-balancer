import unittest
from dataclasses import replace
import aalb_enhanced_handoff_draft as core
from aalb_experiment_v2 import (METHODS, Request,make_trace,trace_hash,run_one,run_matched,queue_probe)

class TestAALBEventModel(unittest.TestCase):
    def test_common_trace_reproducible_and_rates_are_separate(self):
        a=make_trace(core.RING4_NODES,4,100,40,123)
        b=make_trace(core.RING4_NODES,4,100,40,123)
        c=make_trace(core.RING4_NODES,4,100,0,123)
        self.assertEqual(a,b)
        self.assertEqual([replace(x,id=0) for x in a if not x.is_attack],
                         [replace(x,id=0) for x in c if not x.is_attack])
        self.assertNotEqual(trace_hash(a),trace_hash(c))
        self.assertTrue(any(x.is_attack for x in a))
        self.assertTrue(any(not x.is_attack for x in a))

    def test_all_methods_same_trace_and_numerical_bounds(self):
        result,_=run_matched(METHODS,core.RING4_NODES,core.RING4_EDGES,4,25,10,42,
                             [(0,.0),(1,.8),(2.5,.0)])
        self.assertEqual(len({r['traffic_sha256'] for r in result.values()}),1)
        for r in result.values():
            self.assertEqual(r['generated_legit'],r['admitted_legit']+r['rejected_legit'])
            self.assertLessEqual(r['completed_legit'],r['admitted_legit'])
            self.assertLessEqual(r['security_terminated_legit']+r['completed_legit'],r['admitted_legit'])
            self.assertGreaterEqual(r['cpu_utilization_pct'],-1e-7)
            self.assertLessEqual(r['cpu_utilization_pct'],100+1e-7)
            self.assertLessEqual(r['latency_sample_size'],r['completed_legit'])
            if r['mean_e2e_delay_ms'] is not None:
                self.assertAlmostEqual(r['mean_e2e_delay_ms'],r['mean_queue_delay_ms']+
                                       r['mean_propagation_delay_ms']+r['mean_processing_delay_ms'],places=6)

    def test_fifo_queue_positive_wait_and_decomposition(self):
        state=core.FogState(core.RING4_NODES,core.RING4_EDGES)
        info={'src':1,'dst':2,'profile_idx':0,'placement':{'LB':1}}
        free={}
        from collections import defaultdict
        free=defaultdict(float)
        one=queue_probe(state,info,0,free)
        two=queue_probe(state,info,0,free)
        self.assertAlmostEqual(one['queue_ms'],0)
        self.assertGreater(two['queue_ms'],0)
        self.assertAlmostEqual(two['response_ms'],two['propagation_ms']+
                               two['processing_ms']+two['queue_ms'])

    def test_security_compliance_history_static_k1(self):
        req=[Request(1,0.1,1,2,False,2.0)]
        r,_=run_one('original_aalb',core.RING4_NODES,core.RING4_EDGES,req,3,[(0,0),(1,.8)])
        self.assertEqual(r['completed_legit'],1)
        self.assertEqual(r['security_compliant_completion_rate_pct'],0)
        self.assertIsNone(r['upgrade_attempts'])

    def test_adaptive_upgrade_executed(self):
        req=[Request(1,0.1,1,2,False,2.0)]
        r,log=run_one('aalb',core.RING4_NODES,core.RING4_EDGES,req,3,[(0,0),(1,.8)])
        self.assertEqual(r['upgrade_attempts'],1)
        self.assertEqual(r['upgrade_successes'],1)
        self.assertEqual(r['completed_legit'],1)
        self.assertEqual(r['security_compliant_completion_rate_pct'],100)
        self.assertEqual(len([x for x in log if x['event']=='upgrade']),1)

    def test_adaptive_upgrade_failure_terminates(self):
        # 4-node ring at K0 can hold many LB-only sessions but cannot hold
        # the same number of K2 chains; resource pressure causes failure.
        req=[Request(i,0.1+i*.000001,1,2,False,2) for i in range(18)]
        r,log=run_one('aalb',core.RING4_NODES,core.RING4_EDGES,req,3,[(0,0),(1,.8)])
        self.assertGreaterEqual(r['upgrade_failures'],1)
        self.assertEqual(r['security_terminated_legit'],r['upgrade_failures'])
        self.assertEqual(r['upgrade_attempts'],r['upgrade_successes']+r['upgrade_failures'])
        self.assertTrue(any(x['event']=='security_termination' for x in log))

    def test_window_censors_not_completes(self):
        req=[Request(1,.9,1,2,False,1.0)]
        r,_=run_one('aalb',core.RING4_NODES,core.RING4_EDGES,req,1,[(0,0)])
        self.assertEqual(r['admitted_legit'],1)
        self.assertEqual(r['completed_legit'],0)
        self.assertEqual(r['incomplete_at_window_end'],1)

    def test_zero_traffic_nullable_denominators(self):
        r,_=run_one('aalb',core.RING4_NODES,core.RING4_EDGES,[],2,[(0,0)])
        self.assertIsNone(r['admission_rate_pct'])
        self.assertIsNone(r['mean_e2e_delay_ms'])
        self.assertIsNone(r['mandatory_upgrade_success_rate_pct'])
        self.assertEqual(r['cpu_utilization_pct'],0)

    def test_downgrade_after_full_holding_interval(self):
        req=[Request(1,.1,1,2,False,20)]
        r,log=run_one('aalb',core.RING4_NODES,core.RING4_EDGES,req,16,
                      [(0,.8),(2,0)])
        downs=[x for x in log if x['event']=='downgrade']
        self.assertTrue(downs)
        self.assertGreaterEqual(downs[0]['t'],12)

if __name__=='__main__':unittest.main()
