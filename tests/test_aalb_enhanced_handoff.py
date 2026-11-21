"""Targeted checks for the uploaded simulator revision; not full research validation."""
import importlib.util
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sim', __file__.replace('test_aalb_enhanced_handoff.py','aalb_enhanced_handoff_draft.py'))
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

class TestRevision(unittest.TestCase):
    def test_all_methods_smoke(self):
        for method in ('aalb','rr_sfc','lc_sfc','original_aalb'):
            with self.subTest(method=method):
                result = sim.Simulator(sim.RING4_NODES, sim.RING4_EDGES, method).run_static(
                    duration=5.0, req_rate=8.0, lambda_L=8, lambda_A=3, n_runs=1)
                self.assertGreaterEqual(result['throughput'], 0)
                self.assertLessEqual(result['admission_rate'], 1)
                self.assertLessEqual(result['util_cpu'], 1)
    def test_original_endpoints_retained_after_upgrade(self):
        s = sim.Simulator(sim.RING4_NODES, sim.RING4_EDGES, 'aalb')
        self.assertTrue(s.admit_request(13, 2, 3, 0.0, 100.0, 0))
        self.assertEqual((s.state.active[13]['src'], s.state.active[13]['dst']), (2, 3))
        status = s.reconfigure_request(13, 1.0, 2)
        self.assertIn(status, ('ok','blocked'))
        if status == 'ok':
            self.assertEqual((s.state.active[13]['src'], s.state.active[13]['dst']), (2,3))
    def test_cumulative_node_reservation(self):
        state = sim.FogState(sim.RING4_NODES, sim.RING4_EDGES)
        # Individual costs each fit 0.25 core but their combined 0.45 does not.
        state.cpu_avail = {n:0.25 for n in state.nodes}
        placements=sim.find_realizations(state,2,1,3)
        for placement,_,_,_ in placements:
            for n in state.nodes:
                required=sum(sim.VNF_SPECS[v]['cpu'] for v,node in placement.items() if node==n)
                self.assertLessEqual(required,0.25+1e-9)
    def test_throughput_never_exceeds_admissions_per_window(self):
        s=sim.Simulator(sim.RING4_NODES,sim.RING4_EDGES,'aalb')
        r=s.run_static(duration=1.0,req_rate=100.0,lambda_L=100,lambda_A=0,n_runs=1)
        self.assertLessEqual(r['throughput'],r['admitted_legit']/1.0+1e-9)
    def test_cpu_sampling_at_each_second_including_final_interval(self):
        samples = []
        original = sim.FogState.resource_utilization
        def capture(state):
            values = original(state)
            samples.append(values['cpu'])
            return values
        with patch.object(sim.FogState, 'resource_utilization', capture):
            result = sim.Simulator(sim.RING4_NODES, sim.RING4_EDGES, 'aalb').run_static(
                duration=3.0, req_rate=0.0, lambda_L=0, lambda_A=0, n_runs=1)
        self.assertEqual(len(samples), 3)
        self.assertEqual(samples, [0.0, 0.0, 0.0])
        self.assertEqual(result['util_cpu'], 0.0)

    def test_failed_replacement_is_atomic(self):
        state = sim.FogState(sim.RING4_NODES, sim.RING4_EDGES)
        state.commit_realization(1, 0, {'LB':1}, set(), 100.0, [], 1, 2)
        state.cpu_avail[1] = 0.05  # unrelated competing reservations
        before = state.snapshot_avail()
        old = dict(state.active[1])
        with self.assertRaises(ValueError):
            state.commit_realization(1, 2, {'FW':1,'RF':1,'LB':1}, set(), 100.0, [], 1, 2)
        self.assertEqual(before, state.snapshot_avail())
        self.assertEqual(old, state.active[1])

    def test_distinct_baseline_placement(self):
        state = sim.FogState(sim.RING4_NODES, sim.RING4_EDGES)
        state.cpu_avail[1] = 0.6
        rr = sim.baseline_realization(state, 2, 1, 3, 'rr_sfc', 0)
        lc = sim.baseline_realization(state, 2, 1, 3, 'lc_sfc', 0)
        self.assertIsNotNone(rr)
        self.assertIsNotNone(lc)
        self.assertNotEqual(rr[0], lc[0])
        self.assertAlmostEqual(state.cpu_avail[1],0.6)

    def test_legitimate_rate_independent_of_legacy_rate(self):
        sim1 = sim.Simulator(sim.RING4_NODES, sim.RING4_EDGES, 'aalb')
        sim2 = sim.Simulator(sim.RING4_NODES, sim.RING4_EDGES, 'aalb')
        a = sim1.run_static(duration=2, req_rate=0, lambda_L=8, lambda_A=2, n_runs=1)
        b = sim2.run_static(duration=2, req_rate=100, lambda_L=8, lambda_A=2, n_runs=1)
        self.assertEqual(a, b)
        self.assertGreater(a['generated_legit'],0)

    def test_reconfig_smoke(self):
        s=sim.Simulator(sim.RING4_NODES,sim.RING4_EDGES,'aalb')
        r=s.run_reconfig(duration=15,req_rate=.3,attack_trace=[(0,0),(5,.8),(10,0)],n_runs=1)
        self.assertIn('upgrades',r)

if __name__=='__main__': unittest.main()
