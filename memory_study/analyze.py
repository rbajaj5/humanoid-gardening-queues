"""Recompute metrics from retained physical traces and verify the matched design."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
from memory_study.run import CONFIG, HERE, fingerprint


def check_record(path):
    record = json.loads(path.read_text())
    summary, rows, events = record["summary"], record["frames"], record["events"]
    with np.load(path.with_suffix(".npz")) as archive:
        trajectory = {key: archive[key] for key in ("qpos", "qvel", "ctrl")}
    config = summary["fingerprint"]["config"]
    assert summary["fingerprint"] == fingerprint(config), path
    assert summary["gpu_physics"] and "NVIDIA" in summary["device"]
    assert len(rows) == summary["frames"] == len(trajectory["qpos"])
    for key in ("qpos", "qvel", "ctrl"):
        assert np.isfinite(trajectory[key]).all(), (path, key)
    previous = np.zeros(3)
    for i, row in enumerate(rows):
        assert row["time_s"] == round((i+1)*config["control_dt_s"], 8)
        delivered = np.array(row["delivered_ml"])
        assert np.all(delivered >= previous)
        assert sum(delivered)+row["missed_ml"]+row["airborne_ml"] == row["emitted_ml"]
        assert row["reservoir_ml"]+row["emitted_ml"] == config["reservoir_ml"]
        assert sum(row["stored_ml"])+row["overflow_ml"] == sum(delivered)
        assert row["airborne_ml"] == len(record["droplets"][i])
        assert np.all(delivered <= np.array(row["committed_ml"]))
        assert abs(trajectory["qpos"][i, 2]-row["base_height_m"]) < 1e-12
        if summary["policy"] == "queue_aware":
            assert max(row["committed_ml"]) <= config["target_ml"]
        previous = delivered
    final = rows[-1]
    assert summary["delivered_ml"] == final["delivered_ml"]
    excess = int(np.maximum(0, previous-config["target_ml"]).sum())
    shortfall = int(np.maximum(0, config["target_ml"]-previous).sum())
    assert summary["excess_ml"] == excess and summary["shortfall_ml"] == shortfall
    assert summary["task_success"] == bool(excess == 0 and shortfall == 0 and not summary["failures"])
    assert summary["pots_at_target"] == int(np.sum(previous == config["target_ml"]))
    assert summary["emitted_ml"] == final["emitted_ml"]
    assert summary["missed_ml"] == final["missed_ml"]
    assert abs(summary["max_body_tilt_deg"]-max(r["body_tilt_deg"] for r in rows)) < 1e-12
    completed = next((r["time_s"] for r in rows
                      if min(r["delivered_ml"]) >= config["target_ml"]), None)
    if completed is None:
        assert summary["first_all_targets_reached_s"] is None
    else:
        assert abs(summary["first_all_targets_reached_s"]-completed) < 1e-8
    assert abs(summary["hold_time_s"]-config["control_dt_s"]*sum(r["decision"] == "HOLD_STALE" for r in rows)) < 1e-9
    accepted = [e for e in events if e["event"] == "ACCEPT"]
    starts = [e for e in events if e["event"] == "START"]
    assert len(accepted) == summary["commands_accepted"]
    for key, event in (("duplicate_ids_blocked", "DUPLICATE_ID_BLOCKED"),
                       ("commitment_conflicts_blocked", "COMMITMENT_CONFLICT_BLOCKED"),
                       ("old_observations_rejected", "OLD_OBSERVATION_REJECTED")):
        assert summary[key] == sum(e["event"] == event for e in events)
    assert len({e["id"] for e in starts}) == len(starts)
    accepted_by_id = {e["id"]: e for e in accepted}
    assert all(e["id"] in accepted_by_id for e in starts)
    if summary["policy"] in ("identity_freshness", "queue_aware"):
        assert all(0 <= e["t"]-e["observation_time"] <= config["freshness_s"]+1e-8 for e in starts)
        times = [r["observation_generated_s"] for r in rows if r["observation_generated_s"] is not None]
        assert all(a <= b for a, b in zip(times, times[1:]))
    inputs = np.load(path.parent/f"inputs_{summary['seed']}.npz")
    digest = hashlib.sha256(inputs["joint_noise_rad"].tobytes()+inputs["spray_velocity_noise_ms"].tobytes()).hexdigest()
    assert summary["input_tape_sha256"] == digest
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE/"output")
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    summaries = []
    paths = []
    for seed in CONFIG["seeds"]:
        for profile in CONFIG["profiles"]:
            for policy in CONFIG["policies"]:
                path = args.output/f"{profile}_{policy}_{seed}.json"
                if not path.exists():
                    if args.partial:
                        continue
                    raise AssertionError(f"Missing required episode: {path}")
                summaries.append(check_record(path))
                paths.append(path)
    assert summaries, "No evidence"
    by_seed = defaultdict(set)
    groups = defaultdict(list)
    for s in summaries:
        by_seed[s["seed"]].add(s["input_tape_sha256"])
        groups[s["profile"], s["policy"]].append(s)
    assert all(len(hashes) == 1 for hashes in by_seed.values())
    nominal_comparisons = []
    for seed in CONFIG["seeds"]:
        base = args.output/f"nominal_memory_only_{seed}.npz"
        if not base.exists():
            continue
        reference = np.load(base)
        for policy in CONFIG["policies"][1:]:
            path = args.output/f"nominal_{policy}_{seed}.npz"
            if path.exists():
                values = np.load(path)
                nominal_comparisons.append({"seed": seed, "policy": policy,
                    "max_qpos_difference": float(np.max(np.abs(reference["qpos"]-values["qpos"]))),
                    "max_qvel_difference": float(np.max(np.abs(reference["qvel"]-values["qvel"])))})
    aggregates = []
    lines = ["# GPU Memory Study: Measured Results", "", "Exploratory synthetic physics, not vendor or hardware validation.", "",
             "| Profile | Policy | Runs | Target-dose successes | Mean excess ml | Mean shortfall ml | Mean hold s |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for (profile, policy), group in groups.items():
        item = {"profile": profile, "policy": policy, "runs": len(group),
                "successes": sum(s["task_success"] for s in group),
                "mean_excess_ml": float(np.mean([s["excess_ml"] for s in group])),
                "mean_shortfall_ml": float(np.mean([s["shortfall_ml"] for s in group])),
                "mean_hold_s": float(np.mean([s["hold_time_s"] for s in group])),
                "delivered_ml_by_seed": {str(s["seed"]): s["delivered_ml"] for s in group},
                "body_failures": sum(bool(s["failures"]) for s in group)}
        aggregates.append(item)
        lines.append(f"| {profile} | {policy} | {len(group)} | {item['successes']} | {item['mean_excess_ml']:.1f} | {item['mean_shortfall_ml']:.1f} | {item['mean_hold_s']:.2f} |")
    validation = {"episodes_checked": len(summaries), "complete": len(summaries) == 40,
                  "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "frames_checked": sum(s["frames"] for s in summaries),
                  "physical_failures": sum(bool(s["failures"]) for s in summaries),
                  "max_body_tilt_deg": max(s["max_body_tilt_deg"] for s in summaries),
                  "devices": sorted({s["device"] for s in summaries}),
                  "nominal_trajectory_comparisons": nominal_comparisons,
                  "checks": ["source/config/model fingerprints", "matched input arrays", "water conservation every frame",
                             "monotone physical dose", "command uniqueness", "fresh execution gates", "summary recomputation",
                             "finite physical trajectories", "body height matches trajectory"],
                  "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for path in paths for p in (path, path.with_suffix('.npz'))}}
    (args.output/"summaries.json").write_text(json.dumps(summaries, indent=2)+"\n")
    (args.output/"aggregates.json").write_text(json.dumps(aggregates, indent=2)+"\n")
    (args.output/"validation.json").write_text(json.dumps(validation, indent=2)+"\n")
    (args.output/"RESULTS.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))
    print(json.dumps({k: v for k, v in validation.items() if k != "sha256"}, indent=2))


if __name__ == "__main__":
    main()
