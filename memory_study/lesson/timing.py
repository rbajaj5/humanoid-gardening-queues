"""Extract encoder-measured elapsed time, not inferred file timestamps."""

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    source = HERE / "build/render.log"
    text = source.read_text()
    final = [line for line in text.splitlines() if "Lsize=" in line and "elapsed=" in line]
    assert len(final) == 1, "Expected one completed encoding progress line"
    hours, minutes, seconds = re.search(r"elapsed=(\d+):(\d+):([\d.]+)", final[0]).groups()
    elapsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    manifest = json.loads((HERE / "output/movie_frames.json").read_text())
    assert int(re.search(r"frame=\s*(\d+)", final[0]).group(1)) == len(manifest["frames"])
    public_log = text.replace(str(HERE), "memory_study/lesson")
    public_log = "\n".join(line.rstrip() for line in public_log.splitlines()) + "\n"
    public_log_bytes = public_log.encode("utf-8")
    report = {
        "metric": "FFmpeg reported elapsed time for the main animation render and silent-video encoding",
        "seconds": elapsed,
        "measured_runs": 1,
        "method": "Final completed frame/progress line from retained FFmpeg log",
        "progress_line": final[0].strip(),
        "render_log_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "public_log_sha256": hashlib.sha256(public_log_bytes).hexdigest(),
        "public_log_note": "Absolute output directory replaced by repository-relative path; line endings and trailing whitespace normalized. Progress numbers unchanged.",
        "includes": [
            "waiting for rendered OpenGL frames and Pillow composition",
            "CPU libx264 video encoding",
            "silent MP4 finalization",
        ],
        "excludes": [
            "initial Python/model setup",
            "audio assembly",
            "GPU physics simulation",
            "online speech synthesis",
            "final audio/subtitle mux",
            "validation",
            "upload",
        ],
        "cpu": "Intel Core Ultra 9 275HX",
        "installed_ram_gib": 32,
        "gpu": "NVIDIA GeForce RTX 5070 Ti Laptop GPU; 12 GB VRAM",
        "renderer": manifest["renderer"],
        "note": "The GPU physics was recorded previously. One observed render, not a benchmark average or GPU throughput claim.",
    }
    (HERE / "output/render_timing.json").write_text(json.dumps(report, indent=2) + "\n")
    (HERE / "output/render_progress.txt").write_bytes(public_log_bytes)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
