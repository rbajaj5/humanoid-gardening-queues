"""Synthesize public lesson text, retain exact audio, and measure cue durations."""
import asyncio
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess

import edge_tts

HERE = Path(__file__).resolve().parent


async def main():
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    build = HERE / "build"
    build.mkdir(exist_ok=True)
    output = HERE / "output"
    output.mkdir(exist_ok=True)
    timeline = []
    clock = 0.0
    for chapter_index, chapter in enumerate(script["chapters"]):
        for cue_index, cue in enumerate(chapter["cues"]):
            voice = script["chinese_voice" if cue["lang"] == "zh" else "english_voice"]
            fingerprint = hashlib.sha256(json.dumps([cue["text"], voice, script["rate"]],
                                                    ensure_ascii=False).encode()).hexdigest()
            name = f"voice_{chapter_index:02}_{cue_index:02}"
            mp3, wav = build / f"{name}.mp3", build / f"{name}.wav"
            meta = build / f"{name}.json"
            if not (mp3.exists() and meta.exists() and json.loads(meta.read_text())["request_sha256"] == fingerprint):
                await edge_tts.Communicate(cue["text"], voice, rate=script["rate"]).save(str(mp3))
                meta.write_text(json.dumps({"request_sha256": fingerprint}), encoding="utf-8")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ar", "48000",
                            "-ac", "1", "-c:a", "pcm_s16le", str(wav)], check=True)
            import wave
            with wave.open(str(wav), "rb") as stream:
                duration = stream.getnframes() / stream.getframerate()
            cue_duration = duration + 0.65
            timeline.append({**cue, "chapter": chapter_index, "case": chapter["case"],
                             "start": clock, "end": clock + cue_duration, "audio_start": clock + 0.15,
                             "audio_duration": duration, "audio_file": wav.name, "voice": voice,
                             "audio_sha256": hashlib.sha256(wav.read_bytes()).hexdigest()})
            clock += cue_duration
            print(f"Synthesized {name}: {duration:.2f}s", flush=True)
    result = {"duration_s": clock, "tts": "Microsoft online neural voices through edge-tts",
              "edge_tts_version": importlib.metadata.version("edge-tts"), "rate": script["rate"],
              "speedup_after_synthesis": False, "script_sha256": hashlib.sha256((HERE / "script.json").read_bytes()).hexdigest(),
              "cues": timeline}
    (output / "timeline.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Total duration {clock:.2f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
