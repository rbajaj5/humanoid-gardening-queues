"""Small CPU coordinator; physical action outcomes come from CUDA simulation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    generated: float
    volumes: tuple[int, int, int]


@dataclass(frozen=True)
class Command:
    identity: str
    agent: str
    pot: int
    amount: int


class Coordinator:
    def __init__(self, policy, target=60, freshness=0.5):
        self.policy, self.target, self.freshness = policy, target, freshness
        self.latest = None
        self.events = []

    @property
    def checks_freshness(self):
        return self.policy in ("identity_freshness", "queue_aware")

    def observe(self, observation, now):
        if (self.checks_freshness and self.latest is not None
                and observation.generated < self.latest.generated):
            self.events.append({"t": now, "event": "OLD_OBSERVATION_REJECTED",
                                "generated": observation.generated})
            return
        self.latest = observation

    def fresh(self, now):
        return self.latest is not None and 0 <= now-self.latest.generated <= self.freshness+1e-8

    def propose(self, agent, revision, attempt, now):
        if self.latest is None or (self.checks_freshness and not self.fresh(now)):
            self.events.append({"t": now, "event": "PLAN_HELD_STALE", "agent": agent})
            return []
        commands = []
        for pot, amount in enumerate(self.latest.volumes):
            if amount >= self.target:
                continue
            identity = f"{agent}:plan{revision}:pot{pot}"
            if self.policy == "memory_only":
                identity += f":attempt{attempt}"
            commands.append(Command(identity, agent, pot, self.target-amount))
        self.events.append({"t": now, "event": "PLAN", "agent": agent,
                            "revision": revision, "attempt": attempt,
                            "observation_time": self.latest.generated,
                            "observed_ml": list(self.latest.volumes),
                            "commands": [c.identity for c in commands]})
        return commands


class Executor:
    """Single authoritative receiver: atomic acceptance, not distributed consensus.

    Committed volume includes queued, active, and completed commands for this
    watering cycle. It is not released by a timeout. Completion is no permission
    to repeat a non-idempotent dose. Executor restart is outside this experiment.
    """
    def __init__(self, policy, target=60):
        self.policy, self.target = policy, target
        self.ledger = {}
        self.committed = [0, 0, 0]
        self.queue = []
        self.events = []

    def accept(self, command, now):
        old = self.ledger.get(command.identity)
        if old is not None:
            if old != command:
                raise ValueError("Identity reused with a different payload")
            self.events.append({"t": now, "event": "DUPLICATE_ID_BLOCKED",
                                "id": command.identity, "pot": command.pot})
            return False
        if (self.policy == "queue_aware"
                and self.committed[command.pot]+command.amount > self.target):
            self.events.append({"t": now, "event": "COMMITMENT_CONFLICT_BLOCKED",
                                "id": command.identity, "pot": command.pot})
            return False
        self.ledger[command.identity] = command
        self.committed[command.pot] += command.amount
        self.queue.append(command)
        self.events.append({"t": now, "event": "ACCEPT", "id": command.identity,
                            "agent": command.agent, "pot": command.pot,
                            "amount_ml": command.amount,
                            "committed_ml": self.committed.copy()})
        return True

    def start(self, now, coordinator):
        if not self.queue:
            return None
        if coordinator.checks_freshness and not coordinator.fresh(now):
            return None
        command = self.queue.pop(0)
        self.events.append({"t": now, "event": "START", "id": command.identity,
                            "pot": command.pot, "amount_ml": command.amount,
                            "observation_time": None if coordinator.latest is None
                            else coordinator.latest.generated})
        return command
