"""Fit local synthetic speech to exact burned-in caption windows."""
import json
import subprocess
from physical_garden.render import OUT,DURATION


def main():
    segments=json.loads((OUT/"narration.json").read_text())
    command=["ffmpeg","-hide_banner","-loglevel","warning","-y"]
    filters,inputs,checks=[],[],[]
    for i,seg in enumerate(segments):
        path=OUT/f"narration_{i}.wav"
        meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_format","-of","json",str(path)],text=True))
        duration=float(meta["format"]["duration"])
        tempo=max(1.,duration/(seg["end"]-seg["start"]-.3))
        if tempo>1.4:
            raise ValueError(f"Narration segment {i} too long; shorten before publishing")
        command += ["-i",str(path)]
        filters.append(f"[{i}:a]atempo={tempo:.8f},adelay={round(seg['start']*1000)}:all=1[a{i}]")
        inputs.append(f"[a{i}]")
        checks.append({**seg,"raw_duration_s":duration,"tempo":tempo,"fitted_duration_s":duration/tempo})
    filters.append("".join(inputs)+f"amix=inputs={len(inputs)}:normalize=0,apad,atrim=duration={DURATION}[out]")
    command += ["-filter_complex",";".join(filters),"-map","[out]","-ar","48000","-ac","1",str(OUT/"narration.wav")]
    subprocess.run(command,check=True)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","warning","-y","-i",str(OUT/"garden_silent.mp4"),
                    "-i",str(OUT/"narration.wav"),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
                    "-b:a","160k","-t",str(DURATION),"-movflags","+faststart",str(OUT/"humanoid_gardening_gpu.mp4")],check=True)
    (OUT/"audio_validation.json").write_text(json.dumps(checks,indent=2)+"\n")


if __name__=="__main__":
    main()
