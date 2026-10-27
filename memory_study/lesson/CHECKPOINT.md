# Narrated Lesson Checkpoint

October 27, 2026. The user identified that the silent engineering-memory reel
had no voiceover and did not explain its Chinese labels. They requested render
timing beside the video on the GitHub page, not an opening video card.

The earlier 88 s missing-receipt video and the 60 s silent memory-study video
are distinct. This revision explains the latter study's engineering vocabulary.
The measured 40-episode suite is preserved; there are no new physics runs.

Completed: six lesson chapters, 23 speech cues, Mandarin pronunciation and
English neural narration, source-specific definitions, on-screen pinyin and
plain-English definitions, captions, initial/final explanatory pauses, and
full-span recorded replays. Speech timing is 223.94 s; 5,599 video frames at
25 fps yield 223.96 s. No post-synthesis speech speed-up.

Rendering and media verification are complete: all 5,599 frames decoded,
23 audible narration cues and six Mandarin pronunciations are present, and
frame links and 12 encoded image samples passed their checks. This is not ASR
or pronunciation-quality validation. MP4 SHA-256:
`83c8e757f17db4970ed64af3f360cb7e52d0b079b0674fdf9513026b25d6e2d4`.

The retained FFmpeg log reports 284.57 s for the main render/encode. The attempted
process ExitTime timer failed, so no whole-command timing is claimed. The timing
extractor writes `output/render_timing.json` and retains `output/render_progress.txt`.
Setup, speech synthesis, audio assembly, final mux, validation and original physics
are excluded. Timing is placed beside the video, not in a video title card.

Encoded-frame visual inspection covered all six chapters. All 27 tests and the
40,000-state experiment audit passed again; original results are unchanged.
Pending: publish this MP4 as a separate release, then check digest and remote page.

Local speech environment: `../.venv-gardening-voice/Scripts/python.exe`.
GPU/render environment remains `../.venv-laundry-gpu/Scripts/python.exe`.
`script.json` is the exact public text. Only that text is sent to the speech
service. `build/` is ignored. Retained speech hashes and measured cue timings
are in `output/timeline.json`; online synthesis need not reproduce identical bytes.

```powershell
../.venv-gardening-voice/Scripts/python.exe -m memory_study.lesson.speech
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.lesson.render --preview
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.lesson.render
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.lesson.timing
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.lesson.verify
../.venv-laundry-gpu/Scripts/python.exe -m memory_study.analyze
../.venv-laundry-gpu/Scripts/python.exe -m unittest memory_study.test_protocol physical_garden.test_physics test_simulate -v
```

Release target: `engineering-memory-narrated-2026-10-27`.
Front-page links are prepared, but publishing is not complete until the release
asset, digest and remote README have been checked. No other repository is changed.
