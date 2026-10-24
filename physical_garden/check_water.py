"""Independent GPU accounting check, including a parcel deliberately missing all pots."""
import json
import numpy as np
import warp as wp
from physical_garden.model import ROOT,POTS
from physical_garden.water import Water


def main():
    wp.config.kernel_cache_dir=str(ROOT/".warp-cache")
    wp.init()
    if not wp.get_cuda_devices():
        raise RuntimeError("CUDA required")
    water=Water(4)
    origins=[[*xy,.89] for xy in POTS]+[[1.,1.,.89]]
    for point in origins:
        water.step(np.array(point),np.array([0.,0.,-.4]))
    for _ in range(12):
        water.step()
    landed,missed,active=water.snapshot()
    assert landed.tolist()==[1,1,1] and missed==1 and len(active)==0
    result={"gpu_device":wp.get_device("cuda:0").name,"origins_m":origins,
            "landed_ml":landed.tolist(),"missed_ml":missed,"active_ml":len(active),
            "total_emitted_ml":water.emitted,"passed":True}
    (ROOT/"physical_garden/output/water_kernel_check.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
