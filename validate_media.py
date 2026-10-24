import hashlib
import json
import shutil
import subprocess
from simulate import ROOT,OUT


def main():
    video=OUT/"watering_queue_comparison.mp4"
    meta=json.loads(subprocess.check_output([shutil.which("ffprobe"),"-v","error","-count_frames","-show_streams","-show_format","-of","json",str(video)],text=True))
    v=next(s for s in meta["streams"] if s["codec_type"]=="video")
    a=next(s for s in meta["streams"] if s["codec_type"]=="audio")
    assert (v["width"],v["height"],v["avg_frame_rate"],int(v["nb_read_frames"]))==(1920,1080,"25/1",1050)
    assert abs(float(meta["format"]["duration"])-42)<.1
    subprocess.run([shutil.which("ffmpeg"),"-v","error","-xerror","-i",str(video),"-f","null","-"],check=True)
    frames=json.loads((OUT/"movie_frames.json").read_text())
    replays={}
    for profile in ("lost_receipts","permanent_sensor_outage"):
        replays[profile]=[json.loads((OUT/f"replay_{profile}_{p}.json").read_text()) for p in ("timeout_new_id","idempotent_receipt_only","queue_aware")]
    assert len(frames)==1050
    for i,f in enumerate(frames):
        assert f["video_frame"]==i and f["video_time_s"]==i/25
        for replay in replays[f["profile"]]:
            assert replay["frames"][f["trace_index"]]["time_s"]==f["simulation_time_s"]
    for s in json.loads((OUT/"audio_validation.json").read_text()):
        assert s["raw_duration_s"]/s["tempo"] <= s["end"]-s["start"]-.24
    report=dict(passed=True,width=1920,height=1080,fps=25,frames=1050,duration_s=42,audio_codec=a["codec_name"],full_decode="passed",
                frame_links_verified=True,coverage="Six traces, one preselected seed, two profiles; time-downsampled schematic replay",
                video_sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    (OUT/"media_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
