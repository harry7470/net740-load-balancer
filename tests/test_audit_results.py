import csv, unittest
from copy import deepcopy
from pathlib import Path
from audit_results import audit

class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (Path(__file__).parent/'smoke_results'/'raw_per_run.csv').open(newline='') as f:
            cls.rows=list(csv.DictReader(f))

    def test_smoke_grid_passes_consistency_audit(self):
        result=audit(self.rows)
        self.assertTrue(result['passed'])
        self.assertEqual(result['checked_rows'],40)

    def test_rejects_mismatched_traffic(self):
        rows=deepcopy(self.rows)
        rows[0]['traffic_sha256']='different-traffic'
        with self.assertRaisesRegex(ValueError,'Mismatched scenario'):
            audit(rows)

    def test_rejects_inflated_throughput(self):
        rows=deepcopy(self.rows)
        rows[0]['completed_throughput_req_s']='999999'
        with self.assertRaisesRegex(ValueError,'throughput'):
            audit(rows)

    def test_rejects_inconsistent_legitimate_conservation(self):
        rows=deepcopy(self.rows)
        rows[0]['incomplete_legit_at_window_end']='999'
        with self.assertRaisesRegex(ValueError,'session conservation'):
            audit(rows)

    def test_rejects_missing_baseline(self):
        with self.assertRaisesRegex(ValueError,'Missing methods'):
            audit(self.rows[1:])

if __name__=='__main__': unittest.main()
