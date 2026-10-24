"""Save test evidence and a tolerance-based repeatability check of the featured episode."""
import hashlib
import io
import json
import unittest
import numpy as np
from physical_garden.model import ROOT
from physical_garden.test_physics import OUT


def main():
    suite=unittest.defaultTestLoader.loadTestsFromNames(["physical_garden.test_physics","test_simulate"])
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    print(stream.getvalue())
    if not result.wasSuccessful():
        raise AssertionError("Tests failed")
    name="lost_receipts_queue_aware"
    old=json.loads((OUT/f"{name}.json").read_text())
    new=json.loads((OUT/f"reproducibility_{name}.json").read_text())
    a=np.load(OUT/f"{name}.npz")
    b=np.load(OUT/f"reproducibility_{name}.npz")
    diffs={key:float(np.max(np.abs(a[key]-b[key]))) for key in ("qpos","qvel","ctrl")}
    assert diffs["qpos"]<.001 and diffs["qvel"]<.01
    assert old["events"]==new["events"]
    for x,y in zip(old["frames"],new["frames"],strict=True):
        for key in ("delivered_ml","stored_ml","emitted_ml","overflow_ml","decision","queue_length"):
            assert x[key]==y[key],(key,x,y)
    assert old["summary"]["input_tape_sha256"]==new["summary"]["input_tape_sha256"]
    record={"tests_passed":result.testsRun,"test_output":stream.getvalue(),
            "water_kernel_check":json.loads((OUT/"water_kernel_check.json").read_text()),
            "repeatability":{"episode":name,"input_hash_equal":True,"task_events_equal":True,
                             "all_frame_dose_and_decision_metrics_equal":True,
                             "max_absolute_differences":diffs,"qpos_tolerance":.001,"qvel_tolerance":.01,
                             "note":"GPU floating-point dynamics need not be bitwise identical. qpos mixes metres and radians."},
            "preserved_original_task_source_sha256":{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
                for f in ("simulate.py","config.json","test_simulate.py")}}
    (OUT/"validation.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record["repeatability"],indent=2))


if __name__=="__main__":
    main()
