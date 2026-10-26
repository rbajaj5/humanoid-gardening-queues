"""Decode the final MP4 and verify sample links and encoded representative frames."""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image
from memory_study.render import Movie, FPS, DURATION, SEGMENT
from memory_study.run import HERE


def main():
    output = HERE/"output"
    path = output/"engineering_memory_gpu.mp4"
    manifest = json.loads((output/"movie_frames.json").read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["video_sha256"]
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1920, 1080)
    assert video["r_frame_rate"] == f"{FPS}/1"
    assert int(video["nb_frames"]) == FPS*DURATION
    assert abs(float(probe["format"]["duration"])-DURATION) < .05
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], check=True)
    movie = Movie(output)
    for i, link in enumerate(manifest["frames"]):
        assert link["video_frame"] == i and link["video_time_s"] == i/FPS
        for state in link["states"]:
            record = movie.runs[state["run"]][0]
            assert record["frames"][state["state_index"]]["time_s"] == state["simulation_time_s"]
    checks = []
    for segment in range(DURATION//SEGMENT):
        for offset in (5, 10):
            i = (segment*SEGMENT+offset)*FPS
            frame_path = output/f"encoded_{i}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf",
                            f"select=eq(n\\,{i})", "-frames:v", "1", str(frame_path)], check=True)
            encoded = np.asarray(Image.open(frame_path).convert("RGB"), dtype=float)
            expected = np.asarray(movie.frame(i)[0], dtype=float)
            error = float(np.mean(np.abs(encoded-expected)))
            assert error < 7., (i, error)
            checks.append({"frame": i, "mean_absolute_pixel_error": error})
    movie.renderer.close()
    result = {"decoded_frames": FPS*DURATION, "frame_links_checked": len(manifest["frames"]),
              "encoded_frame_checks": checks, "video_sha256": manifest["video_sha256"],
              "audio": "none; explanatory captions burned into the video",
              "coverage": manifest["coverage"]}
    (output/"media_validation.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k: v for k, v in result.items() if k != "coverage"}, indent=2))


if __name__ == "__main__":
    main()
