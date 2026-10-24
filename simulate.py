"""Paired synthetic watering tasks: physical delivery is not a message receipt.

No robotics or fluid engine is claimed. A reliable serial executor transfers
bounded water volumes; the experiment varies only task communication/policy.
"""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parent
OUT = ROOT/"output"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def make_inputs(c, seed, profile):
    if profile not in c["profiles"]:
        raise ValueError(profile)
    rng = random.Random(seed)
    n = round(c["duration_s"]/c["dt_s"])+1
    initial = [rng.uniform(*c["initial_pot_water_range_ml"]) for _ in range(3)]
    flow = [rng.uniform(*c["flow_range_ml_per_s"]) for _ in range(3)]
    travel = [rng.uniform(*c["travel_range_s"]) for _ in range(3)]
    tape = []
    for tick in range(n):
        t = tick*c["dt_s"]
        u = [rng.random() for _ in range(7)]
        command_delay, ack_delay, obs_delay = 1, 1, 0
        command_lost, ack_lost, obs_lost = False, False, False
        if profile == "late_receipts":
            ack_delay = 25+int(20*u[0])
        if profile == "lost_receipts":
            ack_lost = True
        if profile == "temporary_sensor_outage":
            obs_lost = 1 <= t < 10
        if profile == "permanent_sensor_outage":
            obs_lost = t >= 1
        if profile == "combined":
            command_delay, ack_delay, obs_delay = 2+int(6*u[1]), 15+int(30*u[0]), 1+int(5*u[2])
            command_lost, ack_lost = u[3] < .05, u[4] < .35
            obs_lost = 3 <= t < 8 or u[5] < .1
        tape.append(dict(command_delay=command_delay, ack_delay=ack_delay, obs_delay=obs_delay,
                         command_lost=command_lost, ack_lost=ack_lost, obs_lost=obs_lost))
    return dict(seed=seed, profile=profile, initial_water_ml=initial,
                requested_ml=[c["target_water_ml"]-v for v in initial],
                flow_ml_s=flow, travel_s=travel, tape=tape)


def run(c, inputs, policy, retain=False):
    if policy not in c["policies"]:
        raise ValueError(policy)
    dt, tape = c["dt_s"], inputs["tape"]
    need, initial = inputs["requested_ml"], inputs["initial_water_ml"]
    delivered, stored, spills = [0.]*3, list(initial), [0.]*3
    tank, current, issued, serial = c["initial_tank_ml"], 0, None, 0
    last_send, issued_at = -1e9, -1e9
    commands, receipts, observations, queue = [], [], [], []
    accepted, finished, active = {}, {}, None
    executions, duplicates, rejects, messages = [0]*3, 0, 0, 0
    last_obs = None
    done_at, physical_at = None, None
    frames, events = [], []
    holds = 0
    max_conservation_error = 0.

    def emit(tick, event, **kw):
        if retain:
            events.append(dict(time_s=round(tick*dt, 8), event=event, **kw))

    def ack(tick, command_id, pot, success):
        env = tape[tick]
        if not env["ack_lost"]:
            receipts.append((tick+env["ack_delay"], command_id, pot, success))
        else:
            emit(tick, "RECEIPT_LOST", command_id=command_id, pot=pot)

    for tick, env in enumerate(tape):
        t = tick*dt
        # Common receiver deduplication: only ID policy differs between arms.
        due = [x for x in commands if x[0] <= tick]
        commands = [x for x in commands if x[0] > tick]
        for _, cid, pot, dose in due:
            if cid in accepted:
                duplicates += 1
                emit(tick, "DUPLICATE_BLOCKED", command_id=cid, pot=pot)
                if cid in finished:
                    ack(tick, cid, pot, finished[cid])
            else:
                accepted[cid] = (pot, dose)
                queue.append((cid, pot, dose))
                emit(tick, "ENQUEUE", command_id=cid, pot=pot)
        if active is None and queue:
            cid, pot, dose = queue.pop(0)
            active = dict(cid=cid, pot=pot, dose=dose, amount=0., started=t)
            executions[pot] += 1
            emit(tick, "EXECUTE", command_id=cid, pot=pot)
        if active is not None:
            p = active["pot"]
            if t-active["started"] >= inputs["travel_s"][p]:
                amount = min(inputs["flow_ml_s"][p]*dt, active["dose"]-active["amount"], tank)
                tank -= amount
                active["amount"] += amount
                delivered[p] += amount
                absorbed = min(amount, c["pot_capacity_ml"]-stored[p])
                stored[p] += absorbed
                spills[p] += amount-absorbed
                if active["amount"] >= active["dose"]-1e-8 or tank <= 1e-8:
                    ok = active["amount"] >= active["dose"]-1e-8
                    finished[active["cid"]] = ok
                    ack(tick, active["cid"], p, ok)
                    emit(tick, "POUR_FINISHED", command_id=active["cid"], pot=p, success=ok)
                    active = None
        # Deliver snapshots with their original timestamps, never future state.
        if tick % c["observation_period_ticks"] == 0 and not env["obs_lost"]:
            observations.append((tick+env["obs_delay"], tick, delivered.copy()))
        due_obs = [o for o in observations if o[0] <= tick]
        observations = [o for o in observations if o[0] > tick]
        for _, observed_tick, measured in sorted(due_obs):
            if last_obs is None or observed_tick > last_obs[0]:
                last_obs = (observed_tick, measured)
        fresh = last_obs is not None and (tick-last_obs[0])*dt <= c["freshness_s"]+1e-9
        due_acks = [a for a in receipts if a[0] <= tick]
        receipts = [a for a in receipts if a[0] > tick]
        advanced = False
        if current < 3:
            if policy == "queue_aware":
                advanced = (issued is not None and fresh and last_obs[0]*dt > issued_at
                            and last_obs[1][current] >= need[current]-1e-8)
            else:
                advanced = any(p == current and ok for _, cid, p, ok in due_acks)
            if advanced:
                emit(tick, "ADVANCE_OBSERVED" if policy == "queue_aware" else "ADVANCE_RECEIPT", pot=current)
                current += 1
                issued = None
                if current == 3:
                    done_at = t
        # No arm cancels an already-enqueued operation when its plan advances.
        if current < 3:
            if policy == "queue_aware" and not fresh:
                holds += 1
                rejects += 1
            elif issued is None or t-last_send >= c["retry_s"]-1e-9:
                if issued is None or policy == "timeout_new_id":
                    issued = f"plant{current}:cmd{serial}"
                    serial += 1
                    issued_at = t
                last_send = t
                messages += 1
                if not env["command_lost"]:
                    commands.append((tick+env["command_delay"], issued, current, need[current]))
                emit(tick, "SEND" if not env["command_lost"] else "COMMAND_LOST", command_id=issued, pot=current)
        if physical_at is None and all(a >= b-1e-8 for a,b in zip(delivered, need)):
            physical_at = t
        error = abs(tank+sum(stored)+sum(spills)-c["initial_tank_ml"]-sum(initial))
        max_conservation_error = max(max_conservation_error, error)
        if retain:
            frames.append(dict(time_s=round(t,8), pot_water_ml=stored.copy(), delivered_ml=delivered.copy(),
                requested_ml=list(need), spilled_ml=spills.copy(), tank_ml=tank,
                active_pot=active["pot"] if active else None, current_plan_pot=current if current<3 else None,
                queued=len(queue), pending_command_id=issued, observation_age_s=(tick-last_obs[0])*dt if last_obs else None,
                fresh_observation=fresh, executions=executions.copy(), duplicate_attempts_blocked=duplicates,
                controller_state="DONE" if current==3 else ("HOLD_STALE_OBSERVATION" if policy=="queue_aware" and not fresh else "PENDING")))
    excess = sum(max(0,a-b) for a,b in zip(delivered,need))
    physical_complete = all(a >= b-1e-8 for a,b in zip(delivered,need))
    safe_dose = all(a-b <= c["dose_tolerance_ml"] for a,b in zip(delivered,need))
    summary = dict(seed=inputs["seed"], profile=inputs["profile"], policy=policy, input_sha256=digest(inputs),
        physical_complete=physical_complete, dose_safe=safe_dose, safe_task_success=physical_complete and safe_dose,
        controller_declared_done=done_at is not None, controller_done_s=done_at,
        physical_completion_s=physical_at, excess_dose_ml=excess, spilled_ml=sum(spills),
        water_used_ml=c["initial_tank_ml"]-tank, tank_remaining_ml=tank,
        duplicate_pour_starts=sum(max(0,n-1) for n in executions), total_pour_starts=sum(executions),
        duplicate_attempts_blocked=duplicates, stale_hold_s=holds*dt, sent_messages=messages,
        unfinished_plants=sum(a < b-1e-8 for a,b in zip(delivered,need)),
        max_conservation_error_ml=max_conservation_error)
    return dict(summary=summary, frames=frames, events=events)


def aggregate(rows, c):
    out = []
    for profile in c["profiles"]:
        for policy in c["policies"]:
            group = [r for r in rows if r["profile"]==profile and r["policy"]==policy]
            rec = dict(profile=profile, policy=policy, episodes=len(group))
            for k in ("physical_complete", "safe_task_success", "controller_declared_done"):
                rec[k+"_count"] = sum(r[k] for r in group)
            for k in ("excess_dose_ml", "water_used_ml", "spilled_ml", "duplicate_pour_starts", "stale_hold_s", "unfinished_plants"):
                values = [r[k] for r in group]
                rec[k+"_mean"] = statistics.mean(values)
                rec[k+"_sd"] = statistics.stdev(values)
            completed = [r["physical_completion_s"] for r in group if r["physical_completion_s"] is not None]
            rec["completion_s_mean_completed_only"] = statistics.mean(completed) if completed else None
            out.append(rec)
    return out


def main():
    c = json.loads((ROOT/"config.json").read_text())
    OUT.mkdir(exist_ok=True)
    rows = []
    for profile in c["profiles"]:
        for seed in range(c["seed_start"], c["seed_start"]+c["seed_count"]):
            inputs = make_inputs(c, seed, profile)
            retain = seed == c["replay_seed"]
            for policy in c["policies"]:
                r = run(c, inputs, policy, retain)
                rows.append(r["summary"])
                if retain:
                    (OUT/f"replay_{profile}_{policy}.json").write_text(json.dumps(r, separators=(",",":"))+"\n")
            if retain:
                (OUT/f"inputs_{profile}.json").write_text(json.dumps(inputs, separators=(",",":"))+"\n")
        print(f"Completed {profile}", flush=True)
    with (OUT/"episodes.csv").open("w", newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(config=c, python=sys.version, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   config_sha256=hashlib.sha256((ROOT/"config.json").read_bytes()).hexdigest(),
                   episode_count=len(rows), replay_coverage=f"18 complete replays of {len(rows)} episodes: preselected seed {c['replay_seed']}",
                   results=aggregate(rows,c), limitations=["CPU task model, no humanoid/soil/fluid physics", "Synthetic distributions, no horticultural validation",
                   "Safety of requested dose is an input assumption", "No trained controller or real device"])
    (OUT/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary["results"],indent=2))


if __name__ == "__main__":
    main()
