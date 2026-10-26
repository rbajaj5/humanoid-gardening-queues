import unittest
from memory_study.protocol import Command, Coordinator, Executor, Observation


class ProtocolTests(unittest.TestCase):
    def test_resume_identity_is_stable_except_baseline(self):
        for policy in ("memory_only", "idempotent", "identity_freshness", "queue_aware"):
            c = Coordinator(policy)
            c.observe(Observation(0., (0, 0, 0)), 0.)
            first = c.propose("A", 0, 0, 0.)
            second = c.propose("A", 0, 1, 0.)
            self.assertEqual(first == second, policy != "memory_only")

    def test_idempotence_does_not_deduplicate_two_agents_intent(self):
        e = Executor("idempotent")
        self.assertTrue(e.accept(Command("A", "A", 0, 60), 0.))
        self.assertTrue(e.accept(Command("B", "B", 0, 60), 0.))
        self.assertEqual(e.committed[0], 120)

    def test_atomic_budget_blocks_different_ids_for_same_pot(self):
        e = Executor("queue_aware")
        self.assertTrue(e.accept(Command("A", "A", 0, 60), 0.))
        self.assertFalse(e.accept(Command("B", "B", 0, 60), 0.))
        self.assertEqual(e.committed[0], 60)

    def test_retransmission_never_reexecutes_same_id(self):
        e = Executor("idempotent")
        command = Command("one", "A", 0, 60)
        self.assertTrue(e.accept(command, 0.))
        self.assertFalse(e.accept(command, 1.))
        self.assertEqual(len(e.queue), 1)

    def test_identity_payload_collision_fails(self):
        e = Executor("queue_aware")
        e.accept(Command("one", "A", 0, 60), 0.)
        with self.assertRaises(ValueError):
            e.accept(Command("one", "A", 1, 60), 1.)

    def test_old_retrieval_cannot_replace_new_observation(self):
        for policy in ("identity_freshness", "queue_aware"):
            c = Coordinator(policy)
            c.observe(Observation(10., (60, 60, 60)), 10.)
            c.observe(Observation(0., (0, 0, 0)), 10.)
            self.assertEqual(c.propose("A", 1, 0, 10.), [])
            self.assertEqual(c.latest.generated, 10.)

    def test_arrival_order_baseline_uses_old_recall(self):
        c = Coordinator("memory_only")
        c.observe(Observation(10., (60, 60, 60)), 10.)
        c.observe(Observation(0., (0, 0, 0)), 10.)
        self.assertEqual(len(c.propose("A", 1, 0, 10.)), 3)

    def test_queued_work_waits_if_observations_expire(self):
        c, e = Coordinator("queue_aware"), Executor("queue_aware")
        c.observe(Observation(0., (0, 0, 0)), 0.)
        e.accept(Command("one", "A", 0, 60), 0.)
        self.assertIsNone(e.start(1., c))
        self.assertEqual(len(e.queue), 1)
        c.observe(Observation(1., (0, 0, 0)), 1.)
        self.assertIsNotNone(e.start(1., c))

    def test_budget_is_not_released_when_job_starts(self):
        c, e = Coordinator("queue_aware"), Executor("queue_aware")
        c.observe(Observation(0., (0, 0, 0)), 0.)
        e.accept(Command("one", "A", 0, 60), 0.)
        e.start(0., c)
        self.assertFalse(e.accept(Command("two", "B", 0, 60), .1))

    def test_freshness_boundary_and_future_dates(self):
        c = Coordinator("queue_aware")
        c.observe(Observation(2., (0, 0, 0)), 2.)
        self.assertTrue(c.fresh(2.5))
        self.assertFalse(c.fresh(2.5001))
        self.assertFalse(c.fresh(1.))


if __name__ == "__main__":
    unittest.main()
