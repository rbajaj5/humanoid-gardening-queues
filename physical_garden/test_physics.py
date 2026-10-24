"""Audit the retained physical experiment, not only its rendered summary."""
import hashlib
import json
import unittest
from pathlib import Path
import numpy as np
from physical_garden.model import ROOT, POTS, SOIL_Z

OUT = ROOT / "physical_garden/output"
CONFIG = json.loads((ROOT/"physical_garden/config.json").read_text())


def records():
    return [json.loads((OUT/f"{profile}_{policy}.json").read_text())
            for profile in CONFIG["profiles"] for policy in CONFIG["policies"]]


class PhysicalAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = records()

    def test_real_cuda_and_complete_replay(self):
        for run in self.runs:
            s = run["summary"]
            self.assertTrue(s["gpu_physics"])
            self.assertIn("NVIDIA",s["device"])
            self.assertEqual(len(run["frames"]),round(CONFIG["duration_s"]/CONFIG["control_dt_s"]))
            self.assertFalse(s["failures"],s)
            states = np.load(OUT/f"{s['name']}.npz")
            self.assertEqual(len(states["qpos"]),len(run["frames"]))
            self.assertTrue(np.isfinite(states["qpos"]).all())
            # Physically free base, rather than hand-animated joints alone.
            self.assertGreater(np.ptp(states["qpos"][:,0]),1e-5)

    def test_conservation_and_capacities_every_frame(self):
        for run in self.runs:
            for row in run["frames"]:
                self.assertAlmostEqual(row["reservoir_ml"]+sum(row["stored_ml"])+row["overflow_ml"]+
                                       row["missed_ml"]+row["airborne_ml"],CONFIG["reservoir_ml"])
                self.assertTrue(all(0 <= x <= CONFIG["pot_capacity_ml"] for x in row["stored_ml"]))
                self.assertGreaterEqual(row["reservoir_ml"],0)

    def test_shared_noise_and_parameters(self):
        hashes = {r["summary"]["input_tape_sha256"] for r in self.runs}
        self.assertEqual(len(hashes),1)
        tape = np.load(OUT/"matched_inputs.npz")
        self.assertIn(hashlib.sha256(tape["joint_noise_rad"].tobytes()+tape["spray_velocity_noise_ms"].tobytes()).hexdigest(),hashes)
        for run in self.runs:
            self.assertEqual(run["summary"]["config"],CONFIG)

    def test_body_and_aim_envelopes(self):
        for run in self.runs:
            for row in run["frames"]:
                self.assertLess(row["body_tilt_deg"],15)
                self.assertTrue(.65 < row["base_height_m"] < .90)
                if row["valve_open"]:
                    self.assertLess(row["aim_error_m"],CONFIG["pose_tolerance_m"])
                    self.assertGreater(row["nozzle_xyz_m"][2],SOIL_Z)

    def test_task_completion_derived_from_measurements(self):
        for run in self.runs:
            s, last = run["summary"], run["frames"][-1]
            self.assertEqual(s["delivered_ml"],last["delivered_ml"])
            expected = all(CONFIG["dose_ml"] <= x <= CONFIG["dose_ml"]+1 for x in last["delivered_ml"])
            self.assertEqual(s["safe_task_success"],expected and not s["failures"])

    def test_idempotence_and_freshness(self):
        for run in self.runs:
            s = run["summary"]
            starts = [e["id"] for e in run["events"] if e["event"]=="SKILL_START"]
            self.assertEqual(len(starts),len(set(starts)))
            if s["policy"] != "timeout_new_id":
                pots = [e["pot"] for e in run["events"] if e["event"]=="SKILL_START"]
                self.assertEqual(len(pots),len(set(pots)))
            if s["policy"] == "queue_aware":
                for row in run["frames"]:
                    if row["decision"]=="SEND / RETRY":
                        self.assertLessEqual(row["observation_age_s"],CONFIG["freshness_s"]+1e-8)

    def test_source_integrity(self):
        for run in self.runs:
            for path,sha in run["summary"]["source_sha256"].items():
                self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sha,path)


if __name__ == "__main__":
    unittest.main()
