"""Render synchronized measured GPU states; never substitute planned joint poses."""
import argparse
from functools import lru_cache
import hashlib
import json
import subprocess
import textwrap
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from OpenGL.GL import glGetString, GL_RENDERER
from physical_garden.model import ROOT, build, reset

OUT=ROOT/"physical_garden/output"
FPS=25
DURATION=88
COLORS=["#b65749","#307da0","#8f68a3"]
SEGMENTS=[
    (0,7,"This humanoid waters real simulated plant locations. The body and ballistic water parcels run on the NVIDIA GPU."),
    (7,17,"Both sides use the same body controller and disturbances. Each pot should receive sixty millilitres. Completion receipts are lost."),
    (17,30,"On the left, a timeout creates a new command identifier. The executor treats the retry as another watering job, even after the first pour succeeded."),
    (30,43,"On the right, retries keep one identifier. Fresh observations confirm water arriving in the pot, so the coordinator can move to the next plant without a receipt."),
    (43,56,"The blue parcels follow gravity from the measured nozzle pose. Water counts only when a parcel crosses a pot's capture region. The plots report measured delivery, not the intended target."),
    (56,65,"The stable identifier alone blocks duplicate pours, but does not complete the remaining plants when receipts never arrive. Observation-based completion supplies that missing step."),
    (65,78,"There is a cost. Here receipts work, but observations stop. This queue-aware policy holds after the first plant, while the receipt-driven controller continues. More awareness is not automatically better."),
    (78,88,"This is one synthetic configuration, not a reliability claim. The wrist tool is fixed, the water is ballistic, and neither soil physics nor hardware operation has been validated.")
]


@lru_cache(None)
def font(size,bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",size)


def state_index(time_s):
    if time_s < 65:
        profile="lost_receipts"
        f=np.clip((time_s-5)/50,0,1)
    else:
        profile="permanent_observation_loss"
        f=np.clip((time_s-65)/12,0,1)
    return profile,int(round(float(f)*849))


class Movie:
    def __init__(self):
        self.model=build()
        self.data=reset(self.model)
        self.renderer=mujoco.Renderer(self.model,height=590,width=936)
        self.close=mujoco.Renderer(self.model,height=218,width=330)
        self.runs={}
        for profile in ("lost_receipts","permanent_observation_loss","timely"):
            for policy in ("timeout_new_id","queue_aware","idempotent_receipt_only"):
                name=f"{profile}_{policy}"
                self.runs[name]=(json.loads((OUT/f"{name}.json").read_text()),np.load(OUT/f"{name}.npz"))
        self.camera=mujoco.MjvCamera()
        self.camera.lookat[:]=[.20,.17,.70]
        self.camera.distance=2.05
        self.camera.azimuth=55
        self.camera.elevation=-22
        self.detail_camera=mujoco.MjvCamera()
        self.detail_camera.lookat[:]=[.33,.23,.77]
        self.detail_camera.distance=.80
        self.detail_camera.azimuth=65
        self.detail_camera.elevation=-48
        self.renderer.update_scene(self.data,camera=self.camera)
        self.renderer_name=glGetString(GL_RENDERER).decode()

    def scene(self,renderer,camera,particles):
        renderer.update_scene(self.data,camera=camera)
        for point in particles:
            geom=renderer.scene.geoms[renderer.scene.ngeom]
            mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_SPHERE,np.array([.0062,.0062,.0062]),
                              np.asarray(point,dtype=float),np.eye(3).ravel(),np.array([.04,.57,.96,1.]))
            renderer.scene.ngeom+=1
        return Image.fromarray(renderer.render())

    def frame(self,frame):
        t=frame/FPS
        profile,i=state_index(t)
        image=Image.new("RGB",(1920,1080),"#f3f6f7")
        draw=ImageDraw.Draw(image)
        draw.rectangle((0,0,1920,104),fill="#173a3c")
        draw.text((26,13),"Watering is physical. Completion is a coordination problem.",font=font(35,True),fill="white")
        label="COMPLETION RECEIPTS LOST" if profile=="lost_receipts" else "COUNTEREXAMPLE: OBSERVATIONS LOST, RECEIPTS WORK"
        draw.text((27,61),f"SYNTHETIC GPU PHYSICS  |  {label}",font=font(24),fill="#9ee4db")
        linked=[]
        for x,policy,title,color in [(16,"timeout_new_id","Timeout retry: new command ID","#b34d43"),
                                     (968,"queue_aware","Queue-aware: verify before advancing","#16786b")]:
            name=f"{profile}_{policy}"
            record,states=self.runs[name]
            i=min(i,len(record["frames"])-1)
            row=record["frames"][i]
            self.data.qpos[:]=states["qpos"][i]
            self.data.qvel[:]=states["qvel"][i]
            mujoco.mj_forward(self.model,self.data)
            image.paste(self.scene(self.renderer,self.camera,record["droplets"][i]),(x,150))
            detail=self.scene(self.close,self.detail_camera,record["droplets"][i])
            image.paste(detail,(x+596,160))
            draw=ImageDraw.Draw(image)
            draw.rectangle((x+595,159,x+927,379),outline="#62767a",width=2)
            draw.rectangle((x+596,160,x+926,185),fill="#e7eff0")
            draw.text((x+606,161),"Measured nozzle + landing parcels",font=font(17),fill="#173a3c")
            draw.text((x+8,111),title,font=font(29,True),fill=color)
            draw.rectangle((x,701,x+936,740),fill="#e7eff0")
            age=row["observation_age_s"]
            age_text="unavailable" if age is None else f"{age:.2f} s"
            draw.text((x+12,705),f"t = {row['time_s']:05.2f} s    Body tilt {row['body_tilt_deg']:.2f} deg    Observation age {age_text}",font=font(21),fill="#183e40")
            draw.text((x+12,751),f"{row['decision']}  |  queued {row['queue_length']}  |  valve {'OPEN' if row['valve_open'] else 'closed'}",font=font(22,True),fill=color)
            for j,amount in enumerate(row["delivered_ml"]):
                bx=x+14+j*306
                draw.text((bx,790),f"Pot {'ABC'[j]}: {amount} ml",font=font(23,True),fill=COLORS[j])
                draw.rectangle((bx,826,bx+270,846),fill="#dbe3e5")
                draw.rectangle((bx,826,bx+min(amount/300,1)*270,846),fill=COLORS[j])
                goal=bx+60/300*270
                draw.line((goal,820,goal,851),fill="#102a2d",width=3)
            draw.text((x+13,861),f"Target 60 ml each  |  {row['finished_pours']} pours finished  |  {row['duplicates_blocked']} duplicate IDs blocked",font=font(21),fill="#304d53")
            draw.text((x+13,894),f"Reservoir {row['reservoir_ml']:.0f} ml  |  Missed {row['missed_ml']} ml  |  Overflow {row['overflow_ml']:.0f} ml",font=font(21),fill="#304d53")
            linked.append({"run":name,"index":i,"simulation_time_s":row["time_s"]})
        if 56 <= t < 65:
            record=self.runs["lost_receipts_idempotent_receipt_only"][0]["summary"]
            draw.rectangle((210,415,1710,610),fill="#173a3c",outline="#8ecdc3",width=3)
            draw.text((245,435),"Ablation: stable ID + receipt-only coordination",font=font(34,True),fill="white")
            draw.text((245,491),f"Measured delivery: {record['delivered_ml']} ml   |   {record['excess_ml']:.0f} ml excess",font=font(30),fill="#9ee4db")
            draw.text((245,543),"Duplicates stop, but missing receipts still block the next plant.",font=font(29),fill="white")
        if t >= 78:
            draw.rectangle((150,380,1770,650),fill="#173a3c",outline="#8ecdc3",width=3)
            draw.text((188,400),"Bounded result: two mechanisms, one important tradeoff",font=font(35,True),fill="white")
            for y,text in [(462,"Stable command IDs prevent repeat execution."),
                           (508,"Fresh physical observations can replace a missing completion receipt."),
                           (554,"If observations fail, this policy sacrifices progress. A hybrid is future work.")]:
                draw.text((188,y),text,font=font(29),fill="#dcf2ed")
            draw.text((188,606),"One seed / fixed wrist tool / ballistic parcels / no hardware or soil validation",font=font(24),fill="#b7d1ce")
        caption=next(text for a,b,text in SEGMENTS if a <= t < b)
        draw.rectangle((0,935,1920,1080),fill="#112a2e")
        lines=textwrap.wrap(caption,width=118)
        for n,line in enumerate(lines):
            draw.text((36,948+n*34),line,font=font(27),fill="white")
        draw.text((36,1046),"Logged CUDA states, 25 Hz | rigid-body + ballistic-particle simulation | no hardware validation",font=font(19),fill="#afc5c9")
        draw.rectangle((0,1075,int((frame+1)/(FPS*DURATION)*1920),1079),fill="#51c6ab")
        return image,{"video_frame":frame,"video_time_s":t,"profile":profile,"states":linked}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--preview",type=int)
    args=p.parse_args()
    movie=Movie()
    if args.preview is not None:
        path=OUT/f"preview_{args.preview}.jpg"
        movie.frame(args.preview)[0].save(path,quality=95)
        print(path)
        return
    command=["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s","1920x1080","-r",str(FPS),
             "-i","-","-an","-c:v","libx264","-preset","fast","-crf","19","-pix_fmt","yuv420p",
             "-movflags","+faststart",str(OUT/"garden_silent.mp4")]
    log=open(OUT/"render_ffmpeg.log","w")
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
    frames=[]
    for frame in range(FPS*DURATION):
        image,index=movie.frame(frame)
        process.stdin.write(image.tobytes())
        frames.append(index)
        if frame in (0,300,750,1250,1500,1775,2075):
            image.save(OUT/f"preview_{frame}.jpg",quality=95)
        if frame%250==0:
            print(f"Rendered {frame}/{FPS*DURATION}",flush=True)
    process.stdin.close()
    if process.wait()!=0:
        raise RuntimeError("ffmpeg failed; inspect render_ffmpeg.log")
    log.close()
    sources={}
    for name in movie.runs:
        for suffix in ("json","npz"):
            file=OUT/f"{name}.{suffix}"
            sources[file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
    (OUT/"movie_frames.json").write_text(json.dumps({"fps":FPS,"duration_s":DURATION,"width":1920,"height":1080,
        "render_device":movie.renderer_name,"encoding":"CPU libx264; physics is CUDA",
        "coverage":"Complete 34 s lost-receipt and observation-outage timelines for two arms; stable-ID arm summarized from full retained run; timely runs not replayed",
        "source_sha256":sources,"frames":frames},indent=2)+"\n")
    (OUT/"narration.json").write_text(json.dumps([{"start":a,"end":b,"text":text} for a,b,text in SEGMENTS],indent=2)+"\n")


if __name__=="__main__":
    main()
