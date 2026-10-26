"""One compact comparison reel from measured GPU trajectories, with frame links."""
import argparse
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path

import mujoco
import numpy as np
from OpenGL.GL import GL_RENDERER, glGetString
from PIL import Image, ImageDraw, ImageFont
from physical_garden.model import build, reset
from physical_garden.render import font
from memory_study.run import HERE, CONFIG

FPS = 25
SEGMENT = 12
SEED = 45110
CASES = [
    ("nominal", "memory_only", "queue_aware", "Control: a reliable task sequence",
     "Both arms begin with the same plan, body controller and disturbances. The physical target is 60 ml per pot."),
    ("checkpoint_replay", "memory_only", "idempotent", "Session state: resume is not a new intent",
     "At 3 s, the planner replays its plan. A new request ID can repeat a physical dose. Stable logical IDs block that replay."),
    ("shared_snapshot", "identity_freshness", "queue_aware", "Team memory: shared knowledge is not a reservation",
     "Two software planners request the same watering. Distinct IDs are both valid; a shared committed-dose budget blocks the second intent."),
    ("stale_recall", "idempotent", "identity_freshness", "Memory retrieval: arrival time is not observation time",
     "At 20 s, the initial dry-pot snapshot is recalled. Timestamp checks stop old evidence from triggering a new watering plan."),
    ("observation_outage", "memory_only", "queue_aware", "The cost: freshness can stop progress",
     "Observations stop at 1 s. The guarded arm finishes its active pour, then waits. Conservative coordination is not always more productive.")
]
LABELS = {"memory_only": "Memory only / new replay IDs", "idempotent": "Stable logical IDs",
          "identity_freshness": "Stable IDs + observation freshness", "queue_aware": "IDs + freshness + shared commitments"}
DURATION = len(CASES)*SEGMENT
CHINESE_LABELS = ["工作状态", "会话状态", "团队记忆", "记忆片段", "观测时效"]


class Movie:
    def __init__(self, output):
        self.output = output
        self.model = build()
        self.model.vis.quality.offsamples = 0
        self.model.vis.quality.shadowsize = 512
        self.data = reset(self.model)
        self.renderer = mujoco.Renderer(self.model, height=570, width=936)
        self.camera = mujoco.MjvCamera()
        self.camera.lookat[:] = [.20, .17, .60]
        self.camera.distance, self.camera.azimuth, self.camera.elevation = 2.15, 120, -22
        self.renderer.update_scene(self.data, camera=self.camera)
        self.renderer_name = glGetString(GL_RENDERER).decode()
        self.runs = {}
        self.cache = {}
        for profile, left, right, _, _ in CASES:
            for policy in (left, right):
                name = f"{profile}_{policy}_{SEED}"
                self.runs[name] = (json.loads((output/f"{name}.json").read_text()),
                                   np.load(output/f"{name}.npz"))

    def scene(self, name, i):
        record, states = self.runs[name]
        key = name, i
        if key in self.cache:
            return self.cache[key]
        self.data.qpos[:] = states["qpos"][i]
        self.data.qvel[:] = states["qvel"][i]
        mujoco.mj_forward(self.model, self.data)
        self.renderer.update_scene(self.data, camera=self.camera)
        self.renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = False
        self.renderer.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION] = False
        for point in record["droplets"][i]:
            geom = self.renderer.scene.geoms[self.renderer.scene.ngeom]
            mujoco.mjv_initGeom(geom, mujoco.mjtGeom.mjGEOM_SPHERE, np.full(3, .0062),
                              np.asarray(point, dtype=float), np.eye(3).ravel(), np.array([.03, .53, .95, 1.]))
            self.renderer.scene.ngeom += 1
        image = Image.fromarray(self.renderer.render())
        # Cache only the latest sample for each run, not the entire rendered film.
        self.cache = {k: v for k, v in self.cache.items() if k[0] != name}
        self.cache[key] = image
        return image

    def frame(self, index):
        segment_index = min(index//(FPS*SEGMENT), len(CASES)-1)
        profile, left, right, title, caption = CASES[segment_index]
        phase = (index % (FPS*SEGMENT))/(FPS*SEGMENT-1)
        # First ten seconds cover the full episode, final two pause its final state.
        fraction = min(phase*SEGMENT/(SEGMENT-2), 1.)
        image = Image.new("RGB", (1920, 1080), "#f3f6f5")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1920, 110), fill="#173b3a")
        draw.text((28, 12), title, font=font(35, True), fill="white")
        draw.text((28, 65), f"SYNTHETIC GPU PHYSICS | Case {segment_index+1}/5 | seed {SEED} | target 60 ml per pot", font=font(23), fill="#b6e5d8")
        draw.text((1620, 63), CHINESE_LABELS[segment_index],
                  font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26), fill="#b6e5d8")
        links = []
        for x, policy, color in ((16, left, "#b45249"), (968, right, "#176f65")):
            name = f"{profile}_{policy}_{SEED}"
            record, _ = self.runs[name]
            i = int(round(fraction*(len(record["frames"])-1)))
            row = record["frames"][i]
            image.paste(self.scene(name, i), (x, 155))
            draw = ImageDraw.Draw(image)
            draw.text((x+10, 119), LABELS[policy], font=font(28, True), fill=color)
            draw.rectangle((x, 680, x+936, 725), fill="#e4eeeb")
            age = row["observation_age_s"]
            age_label = "none" if age is None else f"{age:.2f} s"
            draw.text((x+12, 690), f"t = {row['time_s']:.2f} s | observation age {age_label} | queued {row['queue_length']}", font=font(22), fill="#173b3a")
            draw.text((x+12, 739), f"{row['decision']} | tilt {row['body_tilt_deg']:.2f} deg | emitted {row['emitted_ml']} ml", font=font(24, True), fill=color)
            for j, amount in enumerate(row["delivered_ml"]):
                bx = x+12+j*306
                draw.text((bx, 783), f"Pot {'ABC'[j]}: {amount} ml", font=font(25, True), fill=color)
                draw.rectangle((bx, 823, bx+270, 843), fill="#d5dfdc")
                draw.rectangle((bx, 823, bx+min(amount/180, 1)*270, 843), fill=color)
                draw.line((bx+90, 817, bx+90, 849), fill="#173b3a", width=3)
            excess = sum(max(0, amount-60) for amount in row["delivered_ml"])
            draw.text((x+12, 860), f"Excess above target: {excess} ml | committed doses {row['committed_ml']}", font=font(22), fill="#173b3a")
            draw.text((x+12, 896), f"Measured capture, not command intent | reservoir {row['reservoir_ml']} ml", font=font(20), fill="#48645d")
            links.append({"run": name, "state_index": i, "simulation_time_s": row["time_s"]})
        draw.rectangle((0, 935, 1920, 1080), fill="#173b3a")
        for j, line in enumerate(textwrap.wrap(caption, width=115)):
            draw.text((30, 949+j*33), line, font=font(27), fill="white")
        draw.text((30, 1045), "Recorded CUDA states | CPU protocol and video encoding | no LLM/vendor execution or hardware validation", font=font(20), fill="#b6d1c9")
        draw.rectangle((0, 1075, int((index+1)/(FPS*DURATION)*1920), 1080), fill="#66c5a2")
        return image, {"video_frame": index, "video_time_s": index/FPS, "profile": profile, "states": links}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE/"output")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    movie = Movie(args.output)
    if args.preview:
        for segment in range(len(CASES)):
            movie.frame((segment*SEGMENT+10)*FPS)[0].save(args.output/f"preview_{segment}.jpg", quality=94)
        return
    path = args.output/"engineering_memory_gpu.mp4"
    with (args.output/"render.log").open("w") as log:
        proc = subprocess.Popen(["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080",
                                 "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "21",
                                 "-preset", "fast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
                                stdin=subprocess.PIPE, stderr=log)
        links = []
        try:
            for i in range(FPS*DURATION):
                image, link = movie.frame(i)
                proc.stdin.write(image.tobytes())
                links.append(link)
                if i % (FPS*SEGMENT) == 10*FPS:
                    image.save(args.output/f"preview_{i//(FPS*SEGMENT)}.jpg", quality=94)
                if i % 250 == 0:
                    print(f"Rendered {i}/{FPS*DURATION}", flush=True)
        finally:
            proc.stdin.close()
            code = proc.wait()
            movie.renderer.close()
        if code:
            raise RuntimeError("Encoding failed")
    coverage = {}
    for name, (record, _) in movie.runs.items():
        shown = {x["state_index"] for link in links for x in link["states"] if x["run"] == name}
        coverage[name] = {"shown_unique_samples": len(shown), "retained_samples": len(record["frames"]),
                          "first_index": min(shown), "last_index": max(shown)}
    manifest = {"width": 1920, "height": 1080, "fps": FPS, "duration_s": DURATION,
                "audio": "silent; burned-in explanatory captions", "renderer": movie.renderer_name,
                "physics": "CUDA (recorded, not rerun while rendering)", "seed": SEED,
                "coverage": coverage, "frames": links,
                "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "video_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (args.output/"movie_frames.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(path)


if __name__ == "__main__":
    main()
