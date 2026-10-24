"""A data-driven schematic replay, deliberately not an articulated-robot movie."""
from functools import lru_cache
import json
import shutil
import subprocess
import textwrap
from PIL import Image,ImageDraw,ImageFont
from simulate import ROOT,OUT

FPS,DURATION=25,42
POLICIES=["timeout_new_id","idempotent_receipt_only","queue_aware"]
TITLES=["Timeout -> new action ID","Stable ID + receipt only","Queue-aware + observed state"]
COLORS=["#ae4c32","#63607d","#007d69"]


@lru_cache(None)
def font(size,bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/"+("segoeuib.ttf" if bold else "segoeui.ttf"),size)


def main():
    cfg=json.loads((ROOT/"config.json").read_text())
    profiles=["lost_receipts","permanent_sensor_outage"]
    replays={profile:[json.loads((OUT/f"replay_{profile}_{p}.json").read_text()) for p in POLICIES] for profile in profiles}
    captions=[
        dict(start=0,end=7,text="Three policies share synthetic plants and inputs. This is task coordination, not a humanoid physics simulation."),
        dict(start=7,end=15,text="Here all completion receipts are lost. New identities turn retries into extra watering. Stable identities stop duplicate pours."),
        dict(start=15,end=23,text="But receipts alone leave the second controller waiting. The queue aware controller uses fresh delivery observations and finishes the three plants."),
        dict(start=23,end=32,text="Now the sensor stream fails instead. Reliable receipts let the first two controllers finish. The queue aware controller refuses to advance on old observations."),
        dict(start=32,end=42,text="The hold leaves two plants unfinished, while the other policies finish without extra water. This is the cost of requiring fresh observations.")]
    encoder=subprocess.Popen([shutil.which("ffmpeg"),"-hide_banner","-loglevel","warning","-y","-f","rawvideo",
        "-pix_fmt","rgb24","-s","1920x1080","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","fast",
        "-crf","19","-pix_fmt","yuv420p","-movflags","+faststart",str(OUT/"watering_silent.mp4")],stdin=subprocess.PIPE)
    index=[]
    try:
        for frame in range(FPS*DURATION):
            vt=frame/FPS
            profile=profiles[0 if vt<23 else 1]
            sim_t=max(0,min(50,(vt-2)*50/21)) if vt<23 else max(0,min(50,(vt-23)*50/14))
            row_index=min(500,int(sim_t/cfg["dt_s"]))
            im=Image.new("RGB",(1920,1080),"#f8faf9")
            d=ImageDraw.Draw(im)
            d.rectangle((0,0,1920,136),fill="#18282b")
            d.text((35,18),"Missing receipts are not missing water.",font=font(40,True),fill="white")
            d.text((35,76),"SYNTHETIC GARDENING COORDINATION  |  CPU task model, not humanoid or fluid physics",font=font(23),fill="#b9d7cd")
            title="Case 1: all completion receipts lost; observations available" if vt<23 else "Case 2: observations lost after 1 s; completion receipts available"
            d.text((35,152),title,font=font(28,True),fill="#18282b")
            d.text((1420,155),f"Seed {cfg['replay_seed']}  |  t = {row_index*.1:.1f} s",font=font(23),fill="#405f63")
            for arm,p in enumerate(POLICIES):
                x=35+arm*635
                color=COLORS[arm]
                row=replays[profile][arm]["frames"][row_index]
                d.rectangle((x,215,x+600,222),fill=color)
                d.text((x,235),TITLES[arm],font=font(27,True),fill=color)
                d.text((x,280),"Reliable serial watering executor",font=font(20),fill="#526766")
                for pot in range(3):
                    cx=x+95+pot*190
                    y=505
                    water=row["pot_water_ml"][pot]
                    h=160*water/cfg["pot_capacity_ml"]
                    d.rectangle((cx-55,y-160,cx+55,y),fill="#e2e8e5",outline="#61756c",width=2)
                    d.rectangle((cx-52,y-h,cx+52,y-2),fill="#5ca8b5")
                    target_y=y-160*cfg["target_water_ml"]/cfg["pot_capacity_ml"]
                    d.line((cx-61,target_y,cx+61,target_y),fill="#163d30",width=3)
                    # Schematic plant identifies the pot; the bar is stored water, not soil depth.
                    d.line((cx,y-165,cx,y-195),fill="#447451",width=4)
                    d.ellipse((cx-27,y-186,cx,y-171),fill="#74a66a")
                    d.ellipse((cx,y-195,cx+27,y-180),fill="#548b59")
                    d.text((cx-29,520),f"Pot {pot+1}",font=font(22,True),fill="#18282b")
                    d.text((cx-42,552),f"{water:.0f} ml",font=font(23),fill="#18282b")
                    if row["active_pot"]==pot:
                        d.text((cx-40,590),"POUR",font=font(21,True),fill=color)
                excess=sum(max(0,a-b) for a,b in zip(row["delivered_ml"],row["requested_ml"]))
                reached=sum(a>=b-1e-8 for a,b in zip(row["delivered_ml"],row["requested_ml"]))
                duplicates=sum(max(0,n-1) for n in row["executions"])
                d.text((x,637),f"Requested doses reached: {reached}/3",font=font(24,True),fill="#18282b")
                d.text((x,678),f"Extra dose: {excess:.1f} ml",font=font(25,True),fill="#a34431" if excess>1 else "#007d69")
                d.text((x,720),f"Duplicate pour starts: {duplicates}",font=font(23),fill="#18282b")
                d.text((x,757),f"Tank: {row['tank_ml']:.0f} ml  |  spilled: {sum(row['spilled_ml']):.0f} ml",font=font(22),fill="#526766")
                age=row["observation_age_s"]
                d.text((x,794),f"Observation age: {age:.1f} s" if age is not None else "No observation yet",font=font(22),fill="#526766")
                state={"DONE":"PLAN COMPLETE","PENDING":"ACTION PENDING","HOLD_STALE_OBSERVATION":"HOLD: OBSERVATION TOO OLD"}[row["controller_state"]]
                d.text((x,843),state,font=font(22,True),fill=color)
                if arm<2:
                    d.line((x+615,235,x+615,885),fill="#d5ded8",width=2)
            d.text((35,904),"Pot bars: synthetic stored-water proxy, ml. Dark line: 300 ml target. Same initial states and message tape within each case.",font=font(20),fill="#526766")
            d.rectangle((0,945,1920,1080),fill="white")
            text=next(s["text"] for s in captions if s["start"]<=vt<s["end"])
            for line_no,line in enumerate(textwrap.wrap(text,width=124)):
                d.text((35,965+line_no*31),line,font=font(25),fill="#18282b")
            d.text((35,1044),"Replay: 1 preselected seed, 2 of 6 profiles. Aggregate experiment: 256 matched seeds x 6 profiles x 3 policies = 4,608 episodes.",font=font(18),fill="#526766")
            encoder.stdin.write(im.tobytes())
            if frame in (300,900):
                im.save(OUT/f"preview_{frame}.jpg",quality=93)
            index.append(dict(video_frame=frame,video_time_s=vt,profile=profile,trace_index=row_index,simulation_time_s=round(row_index*.1,8)))
    finally:
        encoder.stdin.close()
        if encoder.wait()!=0:
            raise RuntimeError("Encoder failed")
    (OUT/"movie_frames.json").write_text(json.dumps(index,separators=(",",":"))+"\n")
    (OUT/"narration.json").write_text(json.dumps(captions,indent=2)+"\n")
    print("Rendered schematic replay")


if __name__=="__main__":
    main()
