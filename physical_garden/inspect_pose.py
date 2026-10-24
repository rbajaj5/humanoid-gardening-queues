"""Render one retained physical pose for model/debug inspection."""
import argparse
import mujoco
import numpy as np
from PIL import Image
from physical_garden.model import ROOT,build,reset


def main():
    p=argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("--index",type=int,default=-1)
    p.add_argument("--azimuth",type=float,default=55)
    args=p.parse_args()
    model=build(); data=reset(model)
    data.qpos[:]=np.load(ROOT/f"physical_garden/output/{args.name}.npz")["qpos"][args.index]
    mujoco.mj_forward(model,data)
    camera=mujoco.MjvCamera()
    camera.lookat[:]=[.22,.17,.72]; camera.distance=1.9
    camera.elevation=-25; camera.azimuth=args.azimuth
    with mujoco.Renderer(model,width=1200,height=900) as renderer:
        renderer.update_scene(data,camera=camera)
        file=ROOT/f"physical_garden/output/pose_{args.name}.jpg"
        Image.fromarray(renderer.render()).save(file,quality=95)
        print(file)
    for i in range(data.ncon):
        c=data.contact[i]
        print(model.geom(c.geom1).name,model.geom(c.geom2).name,c.dist)


if __name__=="__main__":
    main()
