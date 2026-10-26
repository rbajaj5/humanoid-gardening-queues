"""GPU articulated-body + ballistic-parcel experiments; never CPU fallback."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import numpy as np
from physical_garden.model import POTS, ROOT
from physical_garden.run import Physics
from physical_garden.water import Water
from memory_study.protocol import Coordinator, Executor, Observation

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(config):
    files = [HERE / n for n in ("run.py", "protocol.py", "config.json")]
    files += [ROOT / "physical_garden" / n for n in ("model.py", "run.py", "water.py")]
    return {"config": config, "sources": {str(p.relative_to(ROOT)): sha(p) for p in files},
            "model_manifest": sha(ROOT / "output/model_manifest.json")}


def run(physics, profile, policy, seed, config, output):
    dt = config["control_dt_s"]
    if (dt, config["physics_dt_s"], config["water_dt_s"]) != (.04, .002, .01):
        raise ValueError("Only validated 40/2/10 ms integration steps supported")
    physics.restart()
    started = time.perf_counter()
    planner, data = physics.planner, physics.data
    rng = np.random.default_rng(seed)
    count = round(config["duration_s"]/dt)
    noise = rng.normal(0, config["joint_noise_std_rad"], (count, 29))
    spray = rng.normal(0, config["spray_noise_std_ms"], (count, 2))
    tape_hash = hashlib.sha256(noise.tobytes()+spray.tobytes()).hexdigest()
    water = Water(config["reservoir_ml"])
    coordinator = Coordinator(policy, config["target_ml"], config["freshness_s"])
    executor = Executor(policy, config["target_ml"])
    current, transport, observations = None, [], []
    delivered = np.zeros(3, dtype=int)
    pose, feedback = data.ctrl.copy(), np.zeros(29)
    frames, events, states, velocities, controls, droplets = [], [], [], [], [], []
    failures = []
    first_goal = None
    plan_schedule = [(config["initial_plan_s"], "A", 0, 0)]
    if profile == "shared_snapshot":
        plan_schedule.append((config["initial_plan_s"], "B", 0, 0))
    if profile == "checkpoint_replay":
        plan_schedule.append((config["checkpoint_replay_s"], "A", 0, 1))
    if profile == "stale_recall":
        plan_schedule.append((config["stale_recall_s"], "A", 1, 0))
    for k in range(count):
        t = round(k*dt, 8)
        # Observation contents are endogenous; matched exogenous noise is not a
        # claim that controllers receive identical physical observation values.
        if not (profile == "observation_outage" and t >= config["observation_outage_s"]):
            observations.append((t+config["observation_delay_s"], Observation(t, tuple(map(int, delivered)))))
        due = [x for x in observations if x[0] <= t+1e-8]
        observations = [x for x in observations if x[0] > t+1e-8]
        for _, observation in due:
            coordinator.observe(observation, t)
        if profile == "stale_recall" and abs(t-config["stale_recall_s"]) < 1e-8:
            coordinator.observe(Observation(0., (0, 0, 0)), t)
            events.append({"t": t, "event": "RECALLED_INITIAL_SNAPSHOT", "generated": 0.})
        for at, agent, revision, attempt in plan_schedule:
            if abs(t-at) < 1e-8:
                for command in coordinator.propose(agent, revision, attempt, t):
                    transport.append((t+config["command_delay_s"], command))
                if attempt:
                    events.append({"t": t, "event": "PLANNER_CHECKPOINT_REPLAY",
                                   "scope": "plan replay only; executor and physics keep running"})
        due = [x for x in transport if x[0] <= t+1e-8]
        transport = [x for x in transport if x[0] > t+1e-8]
        for _, command in due:
            executor.accept(command, t)
        if current is None:
            command = executor.start(t, coordinator)
            if command is not None:
                current = {"command": command, "start": t, "emitted": 0,
                           "from": pose.copy()+feedback, "last_emission": None}
                feedback = np.zeros(29)
        if current is not None:
            command = current["command"]
            fraction = min(1., (t-current["start"])/config["motion_duration_s"])
            smooth = fraction*fraction*(3-2*fraction)
            pose = (1-smooth)*current["from"]+smooth*physics.targets[command.pot]
            if fraction == 1:
                feedback = planner.nozzle_feedback(data, np.r_[POTS[command.pot], .89], feedback)
        ctrl = planner.balance(pose+feedback+noise[k], data)
        physics.step(ctrl)
        nozzle = data.site_xpos[planner.hands[0]].copy()
        direction = data.xmat[planner.wrist].reshape(3, 3) @ planner.nozzle_axis
        tilt = float(np.degrees(np.arccos(np.clip(1-2*np.sum(data.qpos[4:6]**2), -1, 1))))
        origin = velocity = None
        aim = None
        if current is not None:
            command = current["command"]
            aim = float(np.linalg.norm(nozzle-np.r_[POTS[command.pot], .89]))
            ready = (aim < config["pose_tolerance_m"] and direction[2] < -.97
                     and t-current["start"] >= config["motion_duration_s"])
            if ready and current["emitted"] < command.amount and water.emitted < water.capacity:
                origin, velocity = nozzle, .40*direction+np.r_[spray[k], 0.]
                current["emitted"] += 1
                current["last_emission"] = t
        water.step(origin, velocity)
        delivered, missed, airborne = water.snapshot()
        if (current is not None and current["emitted"] >= current["command"].amount
                and current["last_emission"] is not None and t-current["last_emission"] > .3):
            events.append({"t": t+dt, "event": "PHYSICAL_SKILL_FINISHED",
                           "command": asdict(current["command"]), "delivered_ml": delivered.tolist()})
            current = None
        if np.all(delivered >= config["target_ml"]) and first_goal is None:
            first_goal = t+dt
        if tilt > 15 or not .65 < data.qpos[2] < .90 or not np.isfinite(data.qpos).all():
            failures.append({"t": t+dt, "reason": "body_envelope"})
        if current is not None and t-current["start"] > 12 and current["emitted"] < current["command"].amount:
            failures.append({"t": t+dt, "reason": "tool_alignment_or_source_timeout"})
        age = None if coordinator.latest is None else t-coordinator.latest.generated
        decision = ("EXECUTE" if current else "HOLD_STALE" if executor.queue and coordinator.checks_freshness
                    and not coordinator.fresh(t) else "QUEUED" if executor.queue else "IDLE")
        frames.append({"time_s": round(t+dt, 8), "decision_time_s": t,
                       "delivered_ml": delivered.tolist(), "emitted_ml": water.emitted,
                       "stored_ml": np.minimum(delivered, config["pot_capacity_ml"]).tolist(),
                       "overflow_ml": int(np.maximum(0, delivered-config["pot_capacity_ml"]).sum()),
                       "missed_ml": missed, "airborne_ml": len(airborne),
                       "reservoir_ml": water.capacity-water.emitted,
                       "observation_age_s": age,
                       "observation_generated_s": None if coordinator.latest is None else coordinator.latest.generated,
                       "observed_ml": None if coordinator.latest is None else list(coordinator.latest.volumes),
                       "committed_ml": executor.committed.copy(), "queue_length": len(executor.queue),
                       "decision": decision, "body_tilt_deg": tilt, "base_height_m": float(data.qpos[2]),
                       "nozzle_xyz_m": nozzle.tolist(), "aim_error_m": aim, "valve_open": origin is not None,
                       "active_command": None if current is None else asdict(current["command"])})
        states.append(data.qpos.copy()); velocities.append(data.qvel.copy()); controls.append(ctrl.copy())
        droplets.append(airborne.tolist())
        if failures:
            break
    events += coordinator.events+executor.events
    events.sort(key=lambda e: e["t"])
    summary = {"name": f"{profile}_{policy}_{seed}", "profile": profile, "policy": policy, "seed": seed,
               "gpu_physics": True, "device": physics.device, "robot_mass_kg": float(physics.model.body_subtreemass[1]),
               "integration": "MuJoCo Warp CUDA 2 ms; Warp CUDA ballistic water 10 ms",
               "controller": "CPU hand-authored IK/feedback and protocol; no trained policy or vendor API",
               "input_tape_sha256": tape_hash, "fingerprint": fingerprint(config),
               "delivered_ml": delivered.tolist(), "emitted_ml": water.emitted, "missed_ml": missed,
               "excess_ml": int(np.maximum(0, delivered-config["target_ml"]).sum()),
               "shortfall_ml": int(np.maximum(0, config["target_ml"]-delivered).sum()),
               "pots_at_target": int(np.sum(delivered == config["target_ml"])),
               "task_success": bool(np.all(delivered == config["target_ml"]) and not failures),
               "first_all_targets_reached_s": first_goal, "failures": failures,
               "max_body_tilt_deg": max(r["body_tilt_deg"] for r in frames),
               "commands_accepted": len(executor.ledger),
               "duplicate_ids_blocked": sum(e["event"] == "DUPLICATE_ID_BLOCKED" for e in events),
               "commitment_conflicts_blocked": sum(e["event"] == "COMMITMENT_CONFLICT_BLOCKED" for e in events),
               "old_observations_rejected": sum(e["event"] == "OLD_OBSERVATION_REJECTED" for e in events),
               "hold_time_s": dt*sum(r["decision"] == "HOLD_STALE" for r in frames),
               "frames": len(frames), "wall_seconds": time.perf_counter()-started,
               "packages": {n: importlib.metadata.version(n) for n in ("mujoco", "mujoco-warp", "warp-lang", "numpy")}}
    output.mkdir(parents=True, exist_ok=True)
    name = summary["name"]
    (output/f"{name}.json").write_text(json.dumps({"summary": summary, "frames": frames,
                                                "events": events, "droplets": droplets}, indent=2)+"\n")
    np.savez_compressed(output/f"{name}.npz", qpos=states, qvel=velocities, ctrl=controls)
    input_path = output/f"inputs_{seed}.npz"
    if not input_path.exists():
        np.savez_compressed(input_path, joint_noise_rad=noise, spray_velocity_noise_ms=spray)
    print(json.dumps({k: summary[k] for k in ("name", "delivered_ml", "excess_ml", "shortfall_ml",
                     "task_success", "failures", "wall_seconds")}), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE/"output")
    parser.add_argument("--profile", choices=CONFIG["profiles"])
    parser.add_argument("--policy", choices=CONFIG["policies"])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    profiles = [args.profile] if args.profile else CONFIG["profiles"]
    policies = [args.policy] if args.policy else CONFIG["policies"]
    seeds = [args.seed] if args.seed is not None else CONFIG["seeds"]
    physics = None
    for seed in seeds:
        for profile in profiles:
            for policy in policies:
                path = args.output/f"{profile}_{policy}_{seed}.json"
                if path.exists():
                    previous = json.loads(path.read_text())["summary"]
                    if not args.resume or previous["fingerprint"] != fingerprint(CONFIG):
                        raise RuntimeError(f"Refusing to overwrite or reuse mismatched evidence: {path}")
                    if not path.with_suffix(".npz").exists():
                        raise RuntimeError(f"Missing trajectory: {path}")
                    print("RESUME verified source/config", path.name, flush=True)
                    continue
                if physics is None:
                    physics = Physics()
                run(physics, profile, policy, seed, CONFIG, args.output)


if __name__ == "__main__":
    main()
