import csv
import hashlib
import json
import unittest

from simulate import ROOT, OUT, make_inputs, run, digest, aggregate


class MechanismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads((ROOT/"config.json").read_text())

    def test_repeatable_inputs(self):
        self.assertEqual(make_inputs(self.c,45100,"combined"),make_inputs(self.c,45100,"combined"))
        self.assertNotEqual(digest(make_inputs(self.c,45100,"combined")),digest(make_inputs(self.c,45101,"combined")))

    def test_timely_controls_all_succeed(self):
        inputs = make_inputs(self.c,45100,"timely")
        for p in self.c["policies"]:
            s = run(self.c,inputs,p)["summary"]
            self.assertTrue(s["safe_task_success"])
            self.assertEqual(s["total_pour_starts"],3)

    def test_receipt_loss_not_delivery_loss(self):
        inputs = make_inputs(self.c,45100,"lost_receipts")
        baseline = run(self.c,inputs,"timeout_new_id")["summary"]
        same_id = run(self.c,inputs,"idempotent_receipt_only")["summary"]
        aware = run(self.c,inputs,"queue_aware")["summary"]
        self.assertGreater(baseline["duplicate_pour_starts"],0)
        self.assertGreater(baseline["excess_dose_ml"],0)
        self.assertEqual(same_id["duplicate_pour_starts"],0)
        self.assertFalse(same_id["physical_complete"])
        self.assertTrue(aware["safe_task_success"])

    def test_permanent_sensor_loss_exposes_hold_cost(self):
        inputs = make_inputs(self.c,45100,"permanent_sensor_outage")
        aware = run(self.c,inputs,"queue_aware")["summary"]
        reference = run(self.c,inputs,"idempotent_receipt_only")["summary"]
        self.assertFalse(aware["physical_complete"])
        self.assertFalse(aware["controller_declared_done"])
        self.assertGreater(aware["stale_hold_s"],40)
        self.assertTrue(reference["safe_task_success"])

    def test_conservation_capacity_and_no_future_observations(self):
        for profile in self.c["profiles"]:
            inputs = make_inputs(self.c,45100,profile)
            before = digest(inputs)
            for policy in self.c["policies"]:
                result = run(self.c,inputs,policy,True)
                self.assertEqual(digest(inputs),before)
                self.assertLess(result["summary"]["max_conservation_error_ml"],1e-8)
                for f in result["frames"]:
                    self.assertGreaterEqual(f["tank_ml"],-1e-8)
                    self.assertTrue(all(0 <= x <= self.c["pot_capacity_ml"]+1e-8 for x in f["pot_water_ml"]))
                    self.assertTrue(f["observation_age_s"] is None or f["observation_age_s"] >= 0)
                    self.assertAlmostEqual(f["tank_ml"]+sum(f["pot_water_ml"])+sum(f["spilled_ml"]),
                                           self.c["initial_tank_ml"]+sum(inputs["initial_water_ml"]),places=7)

    def test_no_duplicate_id_can_execute_twice(self):
        inputs = make_inputs(self.c,45100,"combined")
        for policy in self.c["policies"]:
            events = run(self.c,inputs,policy,True)["events"]
            ids = [e["command_id"] for e in events if e["event"]=="EXECUTE"]
            self.assertEqual(len(ids),len(set(ids)))

    def test_freshness_controls_advancement(self):
        r = run(self.c,make_inputs(self.c,45100,"combined"),"queue_aware",True)
        for event in r["events"]:
            if event["event"]=="ADVANCE_OBSERVED":
                f = r["frames"][round(event["time_s"]/self.c["dt_s"])]
                self.assertTrue(f["fresh_observation"])
                p = event["pot"]
                self.assertGreaterEqual(f["delivered_ml"][p]+1e-8,f["requested_ml"][p])


class RetainedTests(unittest.TestCase):
    def test_all_retained_replays_regenerate(self):
        c = json.loads((ROOT/"config.json").read_text())
        for profile in c["profiles"]:
            inputs = json.loads((OUT/f"inputs_{profile}.json").read_text())
            self.assertEqual(inputs,make_inputs(c,c["replay_seed"],profile))
            for policy in c["policies"]:
                old = json.loads((OUT/f"replay_{profile}_{policy}.json").read_text())
                self.assertEqual(old,run(c,inputs,policy,True))

    def test_pairing_and_summary(self):
        c = json.loads((ROOT/"config.json").read_text())
        summary = json.loads((OUT/"summary.json").read_text())
        self.assertEqual(summary["source_sha256"],hashlib.sha256((ROOT/"simulate.py").read_bytes()).hexdigest())
        self.assertEqual(summary["config_sha256"],hashlib.sha256((ROOT/"config.json").read_bytes()).hexdigest())
        with (OUT/"episodes.csv").open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows),c["seed_count"]*len(c["profiles"])*len(c["policies"]))
        for profile in c["profiles"]:
            for seed in range(c["seed_start"],c["seed_start"]+c["seed_count"]):
                group=[r for r in rows if r["profile"]==profile and int(r["seed"])==seed]
                self.assertEqual(len(group),3)
                self.assertEqual(len({r["input_sha256"] for r in group}),1)
        # Re-derive the displayed means/counts directly from the CSV.
        for g in summary["results"]:
            group=[r for r in rows if r["profile"]==g["profile"] and r["policy"]==g["policy"]]
            self.assertEqual(sum(r["safe_task_success"]=="True" for r in group),g["safe_task_success_count"])
            self.assertAlmostEqual(sum(float(r["excess_dose_ml"]) for r in group)/len(group),g["excess_dose_ml_mean"],places=7)


if __name__ == "__main__":
    unittest.main()
