# Narrated Chinese Engineering Lesson

This revision adds the explanation missing from the original silent memory-study
reel. English neural narration and Mandarin pronunciations accompany on-screen
Chinese terms, pinyin, definitions and captions. The video begins directly with
the lesson; rendering time is reported beside it on the repository page.

Six terms: working memory, session state, team memory, memory fragments,
observation freshness and long-term memory. Vendor documentation is linked;
our execution rules and physical analogies are explicitly distinguished from
vendor definitions and claims.

The same 40 CUDA episodes and all earlier results are preserved. No new physics
was run. The video shows seed 45110, pauses for definitions, accelerates each
recorded 40-second comparison, and pauses at the end to explain the result.
It retains the observation-outage shortfall and the 34.28-second hold.

Output: 1920x1080, 25 fps, 223.96 seconds, H264/AAC with burned-in captions and
a selectable subtitle track. A separate SRT, exact script, glossary, timing
record, per-frame links and media audit are included in `memory_study/lesson/`.

Main render + video encode: **4 min 44.57 s (284.57 s)**, one observed run.
FFmpeg's final progress line records this measurement; speech generation,
initial model setup, audio assembly, final mux, validation, upload and the earlier
GPU physics are excluded. Intel Core Ultra 9 275HX, 32 GB RAM, RTX 5070 Ti Laptop
GPU (12 GB); CPU libx264 encoding and OpenGL replay, separate from CUDA physics.

MP4 SHA-256: `83c8e757f17db4970ed64af3f360cb7e52d0b079b0674fdf9513026b25d6e2d4`.

Synthetic speech uses Microsoft online voices through edge-tts 7.3.1: Andrew
Neural in English and Xiaoxiao Neural in Mandarin. Text is synthesized at -5%
rate without subsequently speeding it up to fit. No private data or robot logs
were sent to the speech service. No voice cloning or human-voice claim.

Synthetic simulation only: one humanoid, two software planners in the shared
case, no vendor memory implementation, LLM controller, hardware or soil validation.
The 60-second silent reel and earlier 88-second missing-receipt demonstration
remain available as separate releases.
