import json
import shutil
import subprocess
from simulate import OUT


def main():
    segments=json.loads((OUT/"narration.json").read_text())
    ffmpeg,probe=shutil.which("ffmpeg"),shutil.which("ffprobe")
    command=[ffmpeg,"-hide_banner","-loglevel","warning","-y"]
    filters=[]
    checks=[]
    for i,s in enumerate(segments):
        path=OUT/f"narration_{i}.wav"
        dur=float(json.loads(subprocess.check_output([probe,"-v","error","-show_format","-of","json",str(path)],text=True))["format"]["duration"])
        rate=max(1.,dur/(s["end"]-s["start"]-.25))
        assert rate<=1.4
        command += ["-i",str(path)]
        filters.append(f"[{i}:a]atempo={rate},adelay={s['start']*1000}:all=1[a{i}]")
        checks.append(dict(**s,raw_duration_s=dur,tempo=rate))
    filters.append("".join(f"[a{i}]" for i in range(len(segments)))+f"amix=inputs={len(segments)}:normalize=0,apad,atrim=duration=42[out]")
    subprocess.run(command+["-filter_complex",";".join(filters),"-map","[out]","-ar","48000",str(OUT/"narration.wav")],check=True)
    subprocess.run([ffmpeg,"-hide_banner","-loglevel","warning","-y","-i",str(OUT/"watering_silent.mp4"),"-i",str(OUT/"narration.wav"),
        "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","160k","-t","42","-movflags","+faststart",str(OUT/"watering_queue_comparison.mp4")],check=True)
    (OUT/"audio_validation.json").write_text(json.dumps(checks,indent=2)+"\n")


if __name__=="__main__":
    main()
