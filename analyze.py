"""Generate front-page evidence from retained results; never hardcode counts."""
import hashlib
import io
import json
import unittest

from simulate import ROOT, OUT


def main():
    summary=json.loads((OUT/"summary.json").read_text())
    lines=["# Synthetic Watering Results", "", summary["replay_coverage"], "",
        "CPU task-level simulation only. No humanoid, soil biology or fluid dynamics.", "",
        "Success means all three requested doses delivered with at most 1 ml excess per pot at the 50 s endpoint.",
        "Completion times below condition on reaching all requested doses, even if excess is later delivered;", 
        "they are not safe-completion times. SD describes seeded variation, not uncertainty about real gardens.", "",
        "| Condition | Policy | Dose-safe completion | Excess ml, mean (SD) | Time to all doses, completed only |",
        "| --- | --- | ---: | ---: | ---: |"]
    for r in summary["results"]:
        tm=r["completion_s_mean_completed_only"]
        time="not reached" if tm is None else f"{tm:.2f} s"
        lines.append(f"| {r['profile']} | {r['policy']} | {r['safe_task_success_count']}/{r['episodes']} | "
                     f"{r['excess_dose_ml_mean']:.2f} ({r['excess_dose_ml_sd']:.2f}) | {time} |")
    lines += ["", "## Interpretation", "",
        "Stable command identity plus receiver deduplication removes duplicate dose execution in this model. "
        "Zero excess in the idempotent arms is structural under the fixed-dose and reliable-executor assumptions, not a learned discovery.", "",
        "Fresh observed delivery permits progression without completion receipts. The receipt-only ablation shows "
        "that deduplication alone does not solve a lost-feedback liveness problem.", "",
        "Observation gating also has a cost: a temporary outage delays the queue-aware controller; a permanent "
        "outage leaves the first dose delivered but unverified and two plants unfinished. Here truthful receipts "
        "could support a less conservative hybrid, but that hybrid was not tested.", "",
        "The baseline treats a timeout as justification for a new action ID. It is an explicit failure-mode "
        "baseline, not a claim about every non-queue-aware controller. All arms share receiver deduplication, "
        "a serial executor, tank limits and the same exogenous message tape. No queued pour is silently canceled.", "",
        "Profiles, seeds, doses and thresholds are in config.json. Per-episode outcomes are in output/episodes.csv. "
        "Missing completion times denote unfinished episodes and must not be replaced by zero. "
        "The first 18 complete replays were selected by seed before outcome analysis. No parameter search was performed."]
    (ROOT/"RESULTS.md").write_text("\n".join(lines)+"\n")
    text=io.StringIO()
    tests=unittest.defaultTestLoader.loadTestsFromName("test_simulate")
    result=unittest.TextTestRunner(stream=text,verbosity=2).run(tests)
    if not result.wasSuccessful():
        raise AssertionError(text.getvalue())
    files=[ROOT/"simulate.py",ROOT/"config.json",OUT/"episodes.csv",OUT/"summary.json",ROOT/"RESULTS.md"]
    validation=dict(passed=True,tests_run=result.testsRun,test_output=text.getvalue(),
                    sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (OUT/"validation.json").write_text(json.dumps(validation,indent=2)+"\n")
    print(f"{result.testsRun} tests passed; generated RESULTS.md")


if __name__=="__main__":
    main()
