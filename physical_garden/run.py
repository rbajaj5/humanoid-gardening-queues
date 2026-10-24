"""Matched task protocols driving a real CUDA-integrated articulated humanoid."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import time
import mujoco
import numpy as np
from physical_garden.model import ROOT, POTS, Planner, build, reset

OUT = ROOT / "physical_garden/output"
CONFIG = json.loads((ROOT / "physical_garden/config.json").read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Physics:
    def __init__(self):
        import warp as wp
        import mujoco_warp as mjw
        wp.config.kernel_cache_dir = str(ROOT / ".warp-cache")
        wp.init()
        if not wp.get_cuda_devices():
            raise RuntimeError("CUDA required: refusing CPU substitution")
        self.wp, self.mjw = wp, mjw
        self.model = build()
        self.planner = Planner(self.model)
        self.targets, self.errors = [], []
        for x,y in POTS:
            ctrl, error = self.planner.solve([x,y,.89])
            self.targets.append(ctrl)
            self.errors.append(error)
        print("IK target errors (m):",self.errors,flush=True)
        self.data = reset(self.model)
        with wp.ScopedDevice("cuda:0"):
            self.gm = mjw.put_model(self.model)
            self.gpu = mjw.put_data(self.model,self.data,nconmax=128,njmax=512)
            print("Compile/warm GPU rigid-body kernels",flush=True)
            mjw.step(self.gm,self.gpu)
            wp.synchronize()
            self.gpu = mjw.put_data(self.model,self.data,nconmax=128,njmax=512)
            with wp.ScopedCapture() as cap:
                for _ in range(20):
                    mjw.step(self.gm,self.gpu)
            self.graph = cap.graph
        self.device = wp.get_device("cuda:0").name

    def restart(self):
        self.data = reset(self.model)
        with self.wp.ScopedDevice("cuda:0"):
            fresh = self.mjw.put_data(self.model,self.data,nconmax=128,njmax=512)
            # Captured graph refers to the original data arrays: re-record after reset.
            self.gpu = fresh
            with self.wp.ScopedCapture() as cap:
                for _ in range(20):
                    self.mjw.step(self.gm,self.gpu)
            self.graph = cap.graph
        for _ in range(25):
            self.step(self.data.ctrl.copy())

    def step(self, ctrl):
        self.gpu.ctrl.assign(np.asarray([ctrl],dtype=np.float32))
        self.wp.capture_launch(self.graph)
        self.data.qpos[:] = self.gpu.qpos.numpy()[0]
        self.data.qvel[:] = self.gpu.qvel.numpy()[0]
        self.data.ctrl[:] = ctrl
        self.data.time = float(self.gpu.time.numpy()[0])
        mujoco.mj_forward(self.model,self.data)  # sensing only, no CPU integration


def run(physics, policy, profile, config, prefix=""):
    from physical_garden.water import Water
    physics.restart()
    p, model, data = physics.planner, physics.model, physics.data
    dt = config["control_dt_s"]
    count = round(config["duration_s"]/dt)
    rng = np.random.default_rng(config["seed"])
    disturbances = rng.normal(0,.00035,(count,29))
    spray = rng.normal(0,.035,(count,2))
    tape_hash = hashlib.sha256(disturbances.tobytes()+spray.tobytes()).hexdigest()
    water = Water(round(config["reservoir_ml"]))
    current, queue, transport, receipts, observations = None, [], [], [], []
    ledger, events = set(), []
    pending, next_pot, serial, last_send = None, 0, 0, -100.
    latest, issued_at, duplicates, commands = None, 0., 0, 0
    pose_ctrl = data.ctrl.copy()
    rows, qpos, qvel, controls, droplets = [], [], [], [], []
    failures, finished = [], []
    wall_start = time.perf_counter()
    delivered = np.zeros(3,dtype=int)
    emission_after = None
    declared_at, physical_at = None, None
    for k in range(count):
        t = round(k*dt,8)
        # Observations and receipts have separate channels and completion semantics.
        if not (profile == "permanent_observation_loss" and t >= 1.0):
            observations.append((t+config["observation_delay_s"],t,delivered.copy()))
        due = [o for o in observations if o[0] <= t+1e-8]
        observations = [o for o in observations if o[0] > t+1e-8]
        if due:
            latest = due[-1]
        obs_age = None if latest is None else t-latest[1]
        fresh = obs_age is not None and obs_age <= config["freshness_s"]+1e-8
        for at,cid,pot in list(receipts):
            if at <= t+1e-8:
                events.append({"t":t,"event":"COMPLETION_RECEIPT","id":cid,"pot":pot})
                if policy != "queue_aware" and pot == next_pot:
                    next_pot += 1
                    pending = None
                receipts.remove((at,cid,pot))
        if (policy == "queue_aware" and pending is not None and fresh
                and latest[1] >= issued_at and latest[2][next_pot] >= config["dose_ml"]):
            events.append({"t":t,"event":"VERIFIED_DOSE","id":pending,"pot":next_pot})
            next_pot += 1
            pending = None
        if next_pot == 3 and declared_at is None:
            declared_at = t
        decision = "DONE" if next_pot == 3 else "WAIT FOR COMPLETION"
        if policy == "queue_aware" and not fresh and next_pot < 3:
            decision = "HOLD: STALE OBSERVATION"
        elif t >= .4 and next_pot < 3 and (pending is None or t-last_send >= config["retry_s"]-1e-8):
            if pending is None:
                issued_at = t
            if pending is None or policy == "timeout_new_id":
                pending = f"p{next_pot}-request{serial}"
                serial += 1
            transport.append((t+config["command_delay_s"],pending,next_pot))
            last_send = t
            commands += 1
            decision = "SEND / RETRY"
            events.append({"t":t,"event":"SEND","id":pending,"pot":next_pot})
        for at,cid,pot in list(transport):
            if at <= t+1e-8:
                if cid in ledger:
                    duplicates += 1
                    events.append({"t":t,"event":"DUPLICATE_BLOCKED","id":cid,"pot":pot})
                else:
                    ledger.add(cid)
                    queue.append((cid,pot))
                transport.remove((at,cid,pot))
        if current is None and queue:
            cid,pot = queue.pop(0)
            current = {"id":cid,"pot":pot,"start":t,"emitted":0,"from":pose_ctrl.copy()}
            emission_after = None
            events.append({"t":t,"event":"SKILL_START","id":cid,"pot":pot})
        if current is not None:
            f = min(1.,(t-current["start"])/config["motion_duration_s"])
            f = f*f*(3-2*f)
            pose_ctrl = (1-f)*current["from"]+f*physics.targets[current["pot"]]
        ctrl = p.balance(pose_ctrl+disturbances[k],data)
        physics.step(ctrl)
        nozzle = data.site_xpos[p.hands[0]].copy()
        direction = data.xmat[p.wrist].reshape(3,3) @ p.nozzle_axis
        tilt = float(np.degrees(np.arccos(np.clip(1-2*np.sum(data.qpos[4:6]**2),-1,1))))
        origin = velocity = None
        aim_error = None
        if current is not None:
            target = np.r_[POTS[current["pot"]],.89]
            aim_error = float(np.linalg.norm(nozzle-target))
            can_flow = (aim_error < config["pose_tolerance_m"] and direction[2] < -.97
                        and t-current["start"] >= config["motion_duration_s"])
            if can_flow and current["emitted"] < config["dose_ml"] and water.emitted < water.capacity:
                origin, velocity = nozzle, .40*direction+np.r_[spray[k],0.]
                current["emitted"] += 1
                emission_after = t
        water.step(origin,velocity)
        delivered, missed, airborne = water.snapshot()
        if (current is not None and current["emitted"] >= config["dose_ml"]
                and emission_after is not None and t-emission_after > .3):
            cid,pot = current["id"],current["pot"]
            finished.append({"t":t+dt,"id":cid,"pot":pot})
            events.append({"t":t+dt,"event":"SKILL_FINISHED","id":cid,"pot":pot})
            if profile != "lost_receipts":
                receipts.append((t+dt+.12,cid,pot))
            else:
                events.append({"t":t+dt,"event":"RECEIPT_LOST","id":cid,"pot":pot})
            current = None
        if np.all(delivered >= config["dose_ml"]) and physical_at is None:
            physical_at = t+dt
        if tilt > 15 or not .65 < data.qpos[2] < .90 or not np.isfinite(data.qpos).all():
            failures.append({"t":t+dt,"reason":"body_envelope"})
        if current is not None and t-current["start"] > 12 and current["emitted"] < config["dose_ml"]:
            failures.append({"t":t+dt,"reason":"tool_alignment_or_source_timeout","aim_error_m":aim_error})
        captured = np.minimum(delivered,config["pot_capacity_ml"])
        overflow = float(np.maximum(0,delivered-config["pot_capacity_ml"]).sum())
        rows.append({"time_s":t+dt,"delivered_ml":delivered.tolist(),"stored_ml":captured.tolist(),
                     "reservoir_ml":config["reservoir_ml"]-water.emitted,"missed_ml":missed,
                     "overflow_ml":overflow,"airborne_ml":len(airborne),"emitted_ml":water.emitted,
                     "nozzle_xyz_m":nozzle.tolist(),"aim_error_m":aim_error,"body_tilt_deg":tilt,
                     "base_height_m":float(data.qpos[2]),"observation_age_s":obs_age,
                     "decision":decision,"next_pot":next_pot,"active_pot":current["pot"] if current else None,
                     "valve_open":origin is not None,"pending_id":pending,"duplicates_blocked":duplicates,
                     "queue_length":len(queue),"finished_pours":len(finished)})
        qpos.append(data.qpos.copy()); qvel.append(data.qvel.copy()); controls.append(ctrl.copy())
        droplets.append(airborne.tolist())
        if k % 125 == 0:
            print(profile,policy,f"t={t:.1f} tilt={tilt:.2f} aim={aim_error} ml={delivered}",flush=True)
        if failures:
            break
    name = prefix+profile+"_"+policy
    summary = {"name":name,"policy":policy,"profile":profile,"config":config,"input_tape_sha256":tape_hash,
               "gpu_physics":True,"device":physics.device,"robot_mass_kg":float(model.body_subtreemass[1]),
               "tool_mass_kg":.18,"robot_integration":"MuJoCo Warp CUDA, 2 ms",
               "water_integration":"Warp CUDA ballistic parcels, 10 ms; 1 ml each",
               "delivered_ml":delivered.tolist(),"emitted_ml":water.emitted,"missed_ml":missed,
               "overflow_ml":overflow,"excess_ml":float(np.maximum(0,delivered-config["dose_ml"]).sum()),
               "target_pots_completed":int(np.sum(delivered>=config["dose_ml"])),
               "safe_task_success":bool(np.all(delivered>=config["dose_ml"]) and np.all(delivered<=config["dose_ml"]+1) and not failures),
               "physical_completion_s":physical_at,"declared_completion_s":declared_at,
               "max_body_tilt_deg":max(r["body_tilt_deg"] for r in rows),"failures":failures,
               "commands_sent":commands,"duplicates_blocked":duplicates,"finished_pours":finished,
               "frames":len(rows),"wall_seconds":time.perf_counter()-wall_start,
               "ik_target_errors_m":physics.errors,
               "packages":{x:importlib.metadata.version(x) for x in ["mujoco","mujoco-warp","warp-lang","numpy","scipy"]},
               "source_sha256":{str(f.relative_to(ROOT)):digest(f) for f in
                    [ROOT/"physical_garden"/name for name in ("model.py","run.py","water.py")]},
               "config_sha256":digest(ROOT/"physical_garden/config.json"),
               "limitations":["One seed and calibrated scene; no statistical reliability claim",
                 "Hand-authored IK and fixed wrist tool, not learned dexterity",
                 "External reservoir with no hose tension, pressure, recoil or varying tool-water mass",
                 "Ballistic parcels only; no fluid interactions, leaf interception or soil biology",
                 "Synthetic perfect captured-volume observations when available; volatile ID ledger"]}
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/f"{name}.json").write_text(json.dumps({"summary":summary,"frames":rows,"events":events,"droplets":droplets},indent=2)+"\n")
    np.savez_compressed(OUT/f"{name}.npz",qpos=qpos,qvel=qvel,ctrl=controls)
    np.savez_compressed(OUT/"matched_inputs.npz",joint_noise_rad=disturbances,spray_velocity_noise_ms=spray)
    print(json.dumps(summary,indent=2),flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile",choices=CONFIG["profiles"]+["all"],default="all")
    parser.add_argument("--policy",choices=CONFIG["policies"]+["all"],default="all")
    parser.add_argument("--duration",type=float)
    parser.add_argument("--prefix",default="")
    args = parser.parse_args()
    config = CONFIG.copy()
    if args.duration is not None:
        config["duration_s"] = args.duration
    physics = Physics()
    profiles = config["profiles"] if args.profile == "all" else [args.profile]
    policies = config["policies"] if args.policy == "all" else [args.policy]
    for profile in profiles:
        for policy in policies:
            run(physics,policy,profile,config,args.prefix)


if __name__ == "__main__":
    main()
