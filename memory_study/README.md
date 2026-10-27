# Engineering memory is not authority to act

**[Narrated Chinese engineering lesson: video, glossary and sources](lesson/README.md)**
explains the vocabulary with Mandarin pronunciations, English narration and
captions. It uses the same recorded experiment, not new physics runs. The
original silent compact replay remains available below.

Evidence: [measured results](output/RESULTS.md), [per-episode summaries](output/summaries.json),
[trace validation](output/validation.json). The `complete` field in validation
must be true before treating these files as the completed 40-episode suite.

Exploratory physical-agent experiments inspired by Chinese-language engineering
documentation. This folder extends the calibrated GPU garden without altering
the earlier experiment. It does not implement, benchmark, or find defects in
Alibaba or Tencent products. No psychology sources, paid APIs, or LLM calls.

## Measured findings

The complete suite contains 40 episodes and 40,000 retained states. Both seeds
give the same task-dose outcomes; these are deliberately constructed mechanisms,
not estimates of real-world event frequencies.

| Fault | Insufficient mechanism | Measured delivery per pot | Mechanism that addressed it |
|---|---|---|---|
| Plan replay | New ID per attempt | 120/120/120 ml | Stable logical IDs: 60/60/60 ml |
| Two planners sharing a snapshot | IDs and freshness without shared commitments | 120/120/120 ml | Shared dose budget: 60/60/60 ml |
| Old snapshot recalled for a new plan | Stable IDs without evidence-age checks | 120/120/120 ml | Timestamp checks: 60/60/60 ml |
| Observation outage | Freshness gate prevents further starts | 60/0/0 ml | Availability cost retained: unguarded plans reached 60/60/60 ml |

All nominal arms reached 60/60/60 ml. Guarded outage arms held for 34.28 s of the
40 s episode. There were no body-envelope or alignment-timeout failures; maximum
tilt was 1.288411 degrees. That does not erase the task-dose violations above.
27 tests passed, and the full independent trace audit passed. The film is a
selected replay of one seed, not an animation of aggregate outcomes.

## Documentation and interpretations

Sources read 2026-10-26. Short Chinese labels are retained to support the bilingual
lesson. The operational requirements below are our interpretations, not vendor
safety claims.

| Source and documented concept | Queue-aware interpretation | Experiment |
|---|---|---|
| [Alibaba AgentRun](https://help.aliyun.com/zh/agentrun/memory-storage-overview): long-term memory, history and session state are distinct; state supports resuming tasks. | A resumed plan is not a new physical intent. Preserve logical command identity while reconciling effects already in progress. | `checkpoint_replay`: replay the same plan at 3 s while the executor keeps running. |
| [Tencent Agent Memory](https://cloud.tencent.cn/document/product/1813/132100): short-term state, persistent knowledge and team sharing have separate roles. | Shared knowledge of an unwatered pot does not assign exclusive authority to water it. Reserve both queued and active effects. | `shared_snapshot`: two software planners read the same snapshot and submit separate command IDs to one humanoid. |
| [Alibaba Bailian](https://help.aliyun.com/zh/model-studio/long-term-memory): extracted memory fragments can be affected by temporary information; structured variables and updating are discussed. | Retrieval time is not observation time. A historically true dry-pot observation cannot replace newer physical evidence. | `stale_recall`: initial zero-volume snapshot arrives again at 20 s and a new planning revision runs. |
| [Tencent Memory Hub](https://cloud.tencent.cn/document/product/1813/134572): sharing and permissions govern knowledge assets. | Permission to read a skill is different from committing a resource-consuming action. Add a separate authoritative execution gate. | Receiver-side atomic dose budget, including future queued pours. |
| Same engineering distinction between task context and stored history. | Freshness is useful but costs availability. Missing observations do not imply that the world stopped changing. | `observation_outage`: observations stop at 1 s; guarded policies finish an active dose but do not start another. |

Chinese vocabulary: 工作记忆 (working memory), 长期记忆 (long-term memory),
会话状态 (session state), 团队记忆 (team memory). Vendor categories vary; they are
not treated as synonyms. This simulation implements task state and records,
not a language model's internal attention or a human memory theory.

This suite does not vary context-window size, retrieval accuracy, or memory
capacity. It compares what an execution layer does with available task records.

Some AgentRun deep links redirect to its product overview; that is not evidence
of transaction semantics. We do not infer exactly-once external effects,
consensus, or actuator safety from memory persistence or checkpoint support.

## Comparison and hypotheses

- `memory_only`: latest arriving snapshot; each replay attempt gets a new ID.
- `idempotent`: stable IDs within a logical plan, including checkpoint replay;
  still accepts older observations and distinct agents' duplicate intentions.
- `identity_freshness`: same IDs plus monotone observation timestamps and a
  0.5 s freshness gate at planning and physical skill start. No shared dose budget.
- `queue_aware`: adds atomic per-pot committed-dose accounting across agents.

Exploratory hypotheses: identity should address replay duplication; freshness
should address stale recall; shared commitments should address distinct agents
requesting the same physical effect. The outage is an explicit availability
counterexample, not a failure to be concealed. Nominal runs are a negative control.
The configuration was fixed before inspecting this suite's GPU outcomes, but
this is not an external preregistration or a held-out confirmatory study.

### Operational interpretation

Long-lived task specification: each pot receives 60 ml during this watering
cycle. Active task state: accepted IDs, queued actions, current physical skill,
and observation timestamps. History: accepted/rejected proposals and completed
skills. These have different meanings even if all are stored persistently.

For pot p, define C_p as the sum of volumes of all accepted commands in this
cycle, including commands still queued, executing, or completed. The full guard
accepts a new volume v only if C_p + v <= 60 ml. This atomic receiver-side check
is additional to identical-request deduplication and a timestamp freshness gate.
It prevents the second planner from spending the same task budget under a
different request identity. It is not a theorem about a general robot's safety.

In Chinese engineering terms:

- 恢复会话状态，不应把同一个物理意图变成新的动作。
  Resuming session state should not turn the same physical intent into a new action.
- 共享知识，不等于已经分配好执行权限。
  Shared knowledge does not establish execution authority.
- 记忆的召回时间，不是事实的观测时间。
  Retrieval time is not observation time.
- 已排队但尚未执行的动作，也占用任务预算。
  Queued, unexecuted actions already consume the task budget.
- 缺少新观测时保持等待，可以减少风险，也会降低可用性。
  Waiting without fresh observations can reduce risk and also reduce availability.

## Physical model and inputs

The existing free-base Unitree G1 model has 29 actuated joints, mass and inertia,
ground contact, and a fixed 0.18 kg wrist tool. Robot plus tool mass is approximately
33.52 kg. Joint dynamics use MuJoCo Warp CUDA at 2 ms; 1 ml ballistic water parcels
use Warp CUDA at 10 ms. The task step is 40 ms. Counts come from crossing pot
capture regions, never from a commanded dose or a narrative result.

Five profiles x four policies x two seeds = 40 episodes, 40 s each. Each seed has
the same joint-target and spray-velocity noise arrays in every profile/arm. Message
schedules match across arms within a profile. Observation values are endogenous
and need not match after policies diverge. No outcome-based seed selection.

Each pot's desired dose is 60 ml. Physical storage capacity is 180 ml. Excess
above 60 ml is a task-dose violation, not necessarily overflow or plant damage.
The finite source is 500 ml. The three plants are stationary. In the multi-agent
case, two software planners coordinate one physical robot; this is not two
interacting humanoid bodies.

Each episode includes a one-second physical settling period before its logged
task clock. A row stores the decision at `decision_time_s` and the resulting
physical state at `time_s`, 40 ms later. Observation age is measured at the
decision time. The video uses those same post-step states without interpolation.

## Limits

Hand-authored IK/feedback, not learned dexterity. Ballistic water, not CFD, soil,
leaves, plant biology or hardware validation. Exact synthetic volume observations,
synchronized clocks, trusted messages. One centralized serial executor whose
ledger survives planner replay; no crash/restart durability or distributed consensus
claim. Committed dose stays reserved for the entire watering cycle, including
after completion. Lost water does not automatically release that commitment:
top-up recovery would need a separately specified reconciliation rule.

## Reproduce

Run from the gardening repository using the existing environment:

```powershell
../.venv-laundry-gpu/Scripts/python.exe -m unittest memory_study.test_protocol -v
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.run --resume
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.analyze
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.render
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.verify_media
```

The runner refuses CPU substitution, existing-output overwrite, and resume when
source/config/model fingerprints differ. Per-episode JSON contains decisions,
observations, commands, parcels, device and software versions. NPZ contains
qpos/qvel/control trajectories and matched input arrays. Analysis independently
recomputes outcomes and checks conservation, freshness and provenance.

## Compact physical replay

`output/engineering_memory_gpu.mp4` is a single 60 s, 1920x1080, 25 fps reel with
burned-in explanatory captions and no audio. It shows seed 45110 only, not the
whole study. Each 12 s segment samples the full 40 s episode over approximately
10 s, then holds its terminal state. It does not interpolate or invent physical
states. `movie_frames.json` lists every source index and the exact replay coverage.
Rendering uses local OpenGL; video encoding uses CPU libx264, separate from CUDA
physics. Final verification decodes all frames and compares sampled decoded
frames with the renderer.

The budget guard bounds commanded volume for a pot; physical dose safety also
depends on where parcels actually land. We audit measured capture separately.
There is no inference that 60 ml is biologically safe for arbitrary plants.
Future extensions include learned skill proposals, moving resources, uncertain
sensing, executor-crash recovery, and different humanoid or drone models. Those
would test generalization; this suite alone does not establish it.
