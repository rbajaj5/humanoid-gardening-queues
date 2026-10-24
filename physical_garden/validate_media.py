"""Validate encoded media, physical provenance, synchronized counters and coverage."""
import hashlib
import json
import subprocess
import wave
import numpy as np
from physical_garden.render import OUT,FPS,DURATION,SEGMENTS,state_index


def main():
    video=OUT/"humanoid_gardening_gpu.mp4"
    meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_streams","-show_format","-of","json",str(video)],text=True))
    v=next(s for s in meta["streams"] if s["codec_type"]=="video")
    a=next(s for s in meta["streams"] if s["codec_type"]=="audio")
    assert (v["width"],v["height"],int(v["nb_read_frames"]))==(1920,1080,FPS*DURATION)
    assert abs(float(meta["format"]["duration"])-DURATION)<.1
    assert v["codec_name"]=="h264" and a["codec_name"]=="aac"
    subprocess.run(["ffmpeg","-v","error","-i",str(video),"-f","null","-"],check=True)
    index=json.loads((OUT/"movie_frames.json").read_text())
    coverage={}
    assert len(index["frames"])==FPS*DURATION
    for record in index["frames"]:
        profile,expected=state_index(record["video_time_s"])
        assert record["profile"]==profile
        for state in record["states"]:
            assert state["index"]==expected
            run=json.loads((OUT/f"{state['run']}.json").read_text()) if state["run"] not in coverage else coverage[state["run"]]["run"]
            coverage.setdefault(state["run"],{"run":run,"indices":set()})["indices"].add(expected)
            assert run["frames"][expected]["time_s"]==state["simulation_time_s"]
    for file,sha in index["source_sha256"].items():
        assert hashlib.sha256((OUT/file).read_bytes()).hexdigest()==sha
    audio=json.loads((OUT/"audio_validation.json").read_text())
    for segment,(start,end,text) in zip(audio,SEGMENTS,strict=True):
        assert segment["text"]==text
        assert segment["fitted_duration_s"]<=end-start
    with wave.open(str(OUT/"narration.wav")) as wav:
        samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype=np.int16).astype(float)
    assert np.sqrt(np.mean(samples**2))>100
    result={"video":video.name,"sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
            "bytes":video.stat().st_size,"encoded_frames":int(v["nb_read_frames"]),"duration_s":DURATION,
            "full_decode_passed":True,"audio_present":True,"captions_match_narration":True,
            "source_hashes_match":True,"frame_linkage_passed":True,
            "coverage":{key:{"unique_logged_frames_shown":len(value["indices"]),
                             "retained_frames":len(value["run"]["frames"]),
                             "first":min(value["indices"]),"last":max(value["indices"])} for key,value in coverage.items()}}
    (OUT/"media_validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
