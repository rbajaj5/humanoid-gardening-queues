"""Check narration timing, measured-state links and final encoded media."""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image

from memory_study.lesson.render import Lesson, OUT, BUILD, FPS


def main():
    lesson = Lesson()
    movie = OUT / "engineering_memory_narrated.mp4"
    manifest = json.loads((OUT / "movie_frames.json").read_text())
    assert hashlib.sha256(movie.read_bytes()).hexdigest() == manifest["video_sha256"]
    assert hashlib.sha256(Path(__file__).with_name("render.py").read_bytes()).hexdigest() == manifest["render_source_sha256"]
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(movie)]))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    assert any(s["codec_type"] == "subtitle" for s in probe["streams"])
    assert (video["width"], video["height"], video["r_frame_rate"]) == (1920, 1080, "25/1")
    assert int(video["nb_frames"]) == len(manifest["frames"]) == lesson.frames
    assert abs(float(audio["duration"]) - manifest["duration_s"]) < .08
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(movie), "-f", "null", "-"], check=True)
    end = 0.0
    for cue in lesson.timeline["cues"]:
        assert abs(cue["start"] - end) < 1e-8
        assert cue["start"] <= cue["audio_start"] < cue["audio_start"] + cue["audio_duration"] <= cue["end"]
        end = cue["end"]
    for index, link in enumerate(manifest["frames"]):
        assert link["video_frame"] == index and link["video_time_s"] == index / FPS
        cue = lesson.timeline["cues"][link["cue_index"]]
        assert cue["start"] <= index / FPS < cue["end"] + 1 / FPS
        for state in link["states"]:
            record = lesson.movie.runs[state["run"]][0]
            assert record["frames"][state["state_index"]]["time_s"] == state["simulation_time_s"]
            if link["stage"] == "definition":
                assert state["state_index"] == 0
            if link["stage"] in ("result", "summary"):
                assert state["state_index"] == 999
    for coverage in manifest["coverage"].values():
        assert coverage["first"] == 0 and coverage["last"] == 999
    samples = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(movie), "-map", "0:a:0",
                                       "-f", "s16le", "-ac", "1", "-ar", "48000", "-"])
    decoded_audio = np.frombuffer(samples, dtype="<i2").astype(float)
    audio_checks = []
    for i, cue in enumerate(lesson.timeline["cues"]):
        chunk = decoded_audio[round(cue["audio_start"] * 48000):round((cue["audio_start"] + cue["audio_duration"]) * 48000)]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        assert rms > 20, i
        audio_checks.append({"cue": i, "decoded_rms": rms})
    frame_checks = []
    for chapter in range(6):
        cues = [c for c in lesson.timeline["cues"] if c["chapter"] == chapter]
        selected = [cues[1], next((c for c in cues if c["stage"] == "result"), cues[-1])]
        for offset, cue in enumerate(selected):
            index = round((cue["start"] + .4) * FPS)
            target = BUILD / f"qa_{chapter}_{offset}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(index / FPS), "-i", str(movie),
                            "-frames:v", "1", str(target)], check=True)
            actual = np.asarray(Image.open(target).convert("RGB"), dtype=float)
            expected = np.asarray(lesson.frame(index)[0], dtype=float)
            error = float(np.mean(np.abs(actual - expected)))
            assert error < 7, (index, error)
            frame_checks.append({"frame": index, "mean_absolute_pixel_error": error})
    lesson.movie.renderer.close()
    result = {"complete": True, "decoded_frames": lesson.frames, "frame_links_checked": len(manifest["frames"]),
              "narration_cues": len(audio_checks), "chinese_pronunciations": sum(c["lang"] == "zh" for c in lesson.timeline["cues"]),
              "audio_checks": audio_checks, "encoded_frame_checks": frame_checks, "coverage": manifest["coverage"],
              "duration_s": manifest["duration_s"], "video_sha256": manifest["video_sha256"],
              "note": "Waveform/timing and visual checks; not an ASR or pronunciation-accuracy benchmark"}
    (OUT / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("coverage", "audio_checks")}, indent=2))


if __name__ == "__main__":
    main()
