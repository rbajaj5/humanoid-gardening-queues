"""Add explanations and measured narration timing to unchanged GPU trajectories."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from memory_study.render import Movie, CASES, LABELS, SEED
from physical_garden.render import font

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
BUILD = HERE / "build"
FPS = 25


def wrapped(draw, text, width, selected_font):
    lines, line = [], ""
    for word in text.split():
        candidate = (line + " " + word).strip()
        if line and draw.textlength(candidate, font=selected_font) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


class Lesson:
    def __init__(self):
        self.script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
        self.timeline = json.loads((OUT / "timeline.json").read_text(encoding="utf-8"))
        assert self.timeline["script_sha256"] == hashlib.sha256((HERE / "script.json").read_bytes()).hexdigest()
        self.movie = Movie(HERE.parent / "output")
        self.frames = math.ceil(self.timeline["duration_s"] * FPS)
        self.chinese = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 42)
        self.caption_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 28)

    def frame(self, index):
        t = index / FPS
        cue_index = next((i for i, cue in enumerate(self.timeline["cues"]) if cue["start"] <= t < cue["end"]),
                         len(self.timeline["cues"]) - 1)
        cue = self.timeline["cues"][cue_index]
        chapter = self.script["chapters"][cue["chapter"]]
        profile, left, right, _, _ = CASES[cue["case"]]
        if cue["stage"] == "definition":
            fraction = 0.0
        elif cue["stage"] == "replay":
            fraction = min(1.0, max(0.0, (t - cue["start"]) / max(1 / FPS, cue["end"] - cue["start"] - 1 / FPS)))
        else:
            fraction = 1.0
        image = Image.new("RGB", (1920, 1080), "#f3f6f5")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1920, 105), fill="#173b3a")
        draw.text((28, 8), chapter["term"], font=self.chinese, fill="white")
        draw.text((300, 12), chapter["english"], font=font(39, True), fill="white")
        draw.text((30, 65), chapter["pinyin"], font=font(25), fill="#b6e5d8")
        draw.text((500, 65), f"SYNTHETIC CUDA REPLAY | seed {SEED} | lesson {cue['chapter'] + 1}/6", font=font(23), fill="#b6e5d8")
        draw.text((28, 117), chapter["definition"], font=font(28, True), fill="#173b3a")
        draw.text((28, 160), chapter["source_label"], font=font(22), fill="#48645d")
        links = []
        for x, policy, color in ((16, left, "#b45249"), (968, right, "#176f65")):
            name = f"{profile}_{policy}_{SEED}"
            record, _ = self.movie.runs[name]
            state_index = round(fraction * (len(record["frames"]) - 1))
            row = record["frames"][state_index]
            draw.text((x + 10, 202), LABELS[policy], font=font(27, True), fill=color)
            image.paste(self.movie.scene(name, state_index).resize((800, 487), Image.Resampling.LANCZOS), (x + 68, 240))
            draw = ImageDraw.Draw(image)
            age = "none" if row["observation_age_s"] is None else f"{row['observation_age_s']:.2f} s"
            draw.rectangle((x, 718, x + 936, 756), fill="#e4eeeb")
            draw.text((x + 12, 723), f"sim t = {row['time_s']:.2f} s | observation age {age} | queued {row['queue_length']}", font=font(22), fill="#173b3a")
            draw.text((x + 12, 766), f"{row['decision']} | tilt {row['body_tilt_deg']:.2f} deg | emitted {row['emitted_ml']} ml", font=font(23, True), fill=color)
            for j, amount in enumerate(row["delivered_ml"]):
                bx = x + 12 + j * 306
                draw.text((bx, 806), f"Pot {'ABC'[j]}: {amount} ml", font=font(25, True), fill=color)
                draw.rectangle((bx, 843, bx + 270, 858), fill="#d5dfdc")
                draw.rectangle((bx, 843, bx + min(amount / 180, 1) * 270, 858), fill=color)
                draw.line((bx + 90, 838, bx + 90, 864), fill="#173b3a", width=3)
            excess = sum(max(0, amount - 60) for amount in row["delivered_ml"])
            draw.text((x + 12, 876), f"Excess above 60 ml target: {excess} ml | commitments {row['committed_ml']}", font=font(22), fill="#173b3a")
            links.append({"run": name, "state_index": state_index, "simulation_time_s": row["time_s"]})
        mode = {"definition": "Initial state paused for definition", "replay": "Accelerated measured replay", "result": "Final state paused for explanation", "summary": "Nominal final state repeated for summary"}[cue["stage"]]
        draw.text((28, 912), mode + " | no new physics run | 40 episodes / 2 seeds; this film shows one seed", font=font(20), fill="#48645d")
        draw.rectangle((0, 947, 1920, 1080), fill="#173b3a")
        lines = wrapped(draw, cue.get("caption", cue["text"]), 1850, self.caption_font)
        assert len(lines) <= 3, (cue_index, lines)
        for j, line in enumerate(lines):
            draw.text((28, 951 + 34 * j), line, font=self.caption_font, fill="white")
        draw.rectangle((0, 1075, round((index + 1) / self.frames * 1920), 1080), fill="#66c5a2")
        assert draw.textlength(chapter["definition"], font=font(28, True)) < 1864
        return image, {"video_frame": index, "video_time_s": t, "cue_index": cue_index,
                       "chapter": cue["chapter"], "stage": cue["stage"], "states": links}


def assemble_audio(timeline, duration):
    audio = np.zeros(round(duration * 48000), dtype=np.float64)
    checks = []
    for cue in timeline["cues"]:
        path = BUILD / cue["audio_file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == cue["audio_sha256"]
        with wave.open(str(path), "rb") as stream:
            assert stream.getframerate() == 48000 and stream.getnchannels() == 1
            samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(float)
        start = round(cue["audio_start"] * 48000)
        assert (start + len(samples)) / 48000 <= cue["end"]
        audio[start:start + len(samples)] += samples
        checks.append({"cue": len(checks), "duration_s": len(samples) / 48000,
                       "rms": float(np.sqrt(np.mean(samples ** 2))), "peak": float(np.max(np.abs(samples)))})
        assert checks[-1]["rms"] > 20
    gain = min(2.5, 28000 / max(1, np.max(np.abs(audio))))
    audio *= gain
    with wave.open(str(BUILD / "narration.wav"), "wb") as stream:
        stream.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        stream.writeframes(audio.astype("<i2").tobytes())
    return {"gain": float(gain), "peak": float(np.max(np.abs(audio))), "cues": checks}


def srt_time(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    lesson = Lesson()
    if args.preview:
        for chapter_index in range(6):
            cues = [c for c in lesson.timeline["cues"] if c["chapter"] == chapter_index]
            cue = next((c for c in cues if c["stage"] == "result"), cues[-1])
            lesson.frame(round((cue["start"] + .5) * FPS))[0].save(OUT / f"preview_{chapter_index}.jpg", quality=94)
        lesson.movie.renderer.close()
        return
    final = OUT / "engineering_memory_narrated.mp4"
    silent = BUILD / "silent.mp4"
    audio_check = assemble_audio(lesson.timeline, lesson.frames / FPS)
    subtitles = OUT / "captions.srt"
    subtitles.write_text("\n\n".join(
        f"{i + 1}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c.get('caption', c['text'])}"
        for i, c in enumerate(lesson.timeline["cues"])), encoding="utf-8")
    with (BUILD / "render.log").open("w") as log:
        process = subprocess.Popen(["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080",
                                    "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "21", "-preset", "fast",
                                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent)], stdin=subprocess.PIPE, stderr=log)
        links = []
        try:
            for index in range(lesson.frames):
                image, link = lesson.frame(index)
                process.stdin.write(image.tobytes())
                links.append(link)
                if index % 500 == 0:
                    print(f"Rendered {index}/{lesson.frames}", flush=True)
        finally:
            process.stdin.close()
            code = process.wait()
            lesson.movie.renderer.close()
        if code:
            raise RuntimeError("Video encoding failed")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(BUILD / "narration.wav"),
                    "-i", str(subtitles), "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-c:s", "mov_text", "-metadata:s:a:0", "language=mul",
                    "-metadata:s:s:0", "language=mul", "-movflags", "+faststart", str(final)], check=True)
    coverage = {}
    for name, (record, _) in lesson.movie.runs.items():
        indices = {s["state_index"] for link in links for s in link["states"] if s["run"] == name}
        coverage[name] = {"shown": len(indices), "retained": len(record["frames"]), "first": min(indices), "last": max(indices)}
    manifest = {"duration_s": lesson.frames / FPS, "fps": FPS, "frames": links, "coverage": coverage,
                "seed": SEED, "audio": audio_check, "physics": "Preserved CUDA states; no new simulation",
                "renderer": lesson.movie.renderer_name, "script_sha256": lesson.timeline["script_sha256"],
                "render_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "video_sha256": hashlib.sha256(final.read_bytes()).hexdigest()}
    (OUT / "movie_frames.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(final, flush=True)


if __name__ == "__main__":
    main()
