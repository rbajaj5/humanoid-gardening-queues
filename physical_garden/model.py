"""Free-base G1 with a mass-bearing wrist tool and three stationary planters."""
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
POTS = np.array([[.25, .36], [.41, .23], [.26, .10]])
SOIL_Z = .70
POT_RADIUS = .070
HAND = {"left": np.array([.085, .003, 0.]), "right": np.array([.085, -.003, 0.])}


def build():
    source = ROOT / "models/unitree_g1"
    root = ET.parse(source / "g1.xml").getroot()
    root.find("compiler").set("meshdir", str(source / "assets"))
    root.find("option").set("timestep", ".002")
    root.find("option").set("iterations", "50")
    root.remove(root.find("keyframe"))
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="1920", offheight="1080")
    ET.SubElement(visual, "headlight", diffuse=".7 .7 .7", ambient=".35 .35 .35")
    ET.SubElement(root.find("asset"), "texture", type="skybox", builtin="gradient", rgb1=".83 .88 .86",
                  rgb2=".83 .88 .86", width="64", height="384")
    world = root.find("worldbody")
    ET.SubElement(world, "light", pos="-1 2 3", dir="0 0 -1", diffuse=".7 .7 .7")
    ET.SubElement(world, "geom", name="floor", type="plane", size="3 3 .1",
                  rgba=".83 .88 .86 1", friction=".8 .01 .001")
    ET.SubElement(world, "geom", name="bench", type="box", pos=".38 .23 .58",
                  size=".20 .27 .025", rgba=".47 .56 .59 1")
    for x in (.20, .55):
        for y in (0., .46):
            ET.SubElement(world, "geom", type="box", pos=f"{x} {y} .28",
                          size=".015 .015 .28", rgba=".3 .4 .43 1")
    colors = [".7 .3 .25 1", ".19 .46 .62 1", ".55 .40 .64 1"]
    for i, (x, y) in enumerate(POTS):
        ET.SubElement(world, "geom", name=f"pot_{i}", type="cylinder", pos=f"{x} {y} .65",
                      size=f"{POT_RADIUS} .045", rgba=colors[i])
        ET.SubElement(world, "geom", name=f"soil_{i}", type="cylinder", pos=f"{x} {y} .697",
                      size=".064 .003", rgba=".28 .25 .21 1")
        # Leaves are visual markers, not an irrigation/biology model.
        for j in range(5):
            a = j*2*np.pi/5
            endpoint = [x+.045*np.cos(a), y+.045*np.sin(a), .75 + .01*(j%2)]
            ET.SubElement(world, "geom", type="capsule", fromto=f"{x} {y} .70 " + " ".join(map(str, endpoint)),
                          size=".009", rgba=".20 .52 .29 1", contype="0", conaffinity="0")
    for side, point in HAND.items():
        body = root.find(f".//body[@name='{side}_wrist_yaw_link']")
        ET.SubElement(body, "site", name=f"{side}_hand_tip", pos=" ".join(map(str, point)),
                      size=".007", rgba=".1 .7 .55 1")
    # A rigid calibrated wrist attachment avoids pretending to simulate dexterous fingers.
    left = root.find(".//body[@name='left_wrist_yaw_link']")
    tool = ET.SubElement(left, "body", name="watering_tool_body")
    ET.SubElement(tool, "geom", name="watering_tool", type="capsule", fromto=".025 .003 0 .085 .003 0",
                  size=".014", mass=".18", rgba=".09 .65 .74 1", contype="0", conaffinity="0")
    return mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))


def reset(model):
    d = mujoco.MjData(model)
    key = ET.parse(ROOT / "models/unitree_g1/g1.xml").find("keyframe/key")
    d.qpos[:36] = np.fromstring(key.get("qpos"), sep=" ")
    d.ctrl[:] = np.fromstring(key.get("ctrl"), sep=" ")
    mujoco.mj_forward(model, d)
    return d


class Planner:
    """Offline geometric IK. Only joint targets are passed to physical integration."""
    def __init__(self, model):
        self.model, self.data = model, reset(model)
        d = self.data
        self.home = d.qpos.copy()
        self.vars = np.r_[np.arange(3), np.arange(7, 36)]
        self.previous = self.home[self.vars].copy()
        self.feet = [model.body(s+"_ankle_roll_link").id for s in ("left", "right")]
        self.fp = d.xpos[self.feet].copy()
        self.fr = d.xmat[self.feet].copy().reshape(2, 3, 3)
        self.com_xy = d.subtree_com[1, :2].copy()
        self.hands = [model.site(s+"_hand_tip").id for s in ("left", "right")]
        self.home_hands = d.site_xpos[self.hands].copy()
        self.wrist = model.body("left_wrist_yaw_link").id
        self.rotation = d.xmat[self.wrist].copy().reshape(3, 3)
        self.nozzle_axis = self.rotation.T @ np.array([0., 0., -1.])
        self.arm_actuators = [a for a in range(29) if model.actuator(a).name.startswith(
            ("left_shoulder", "left_elbow", "left_wrist"))]
        self.arm_dofs = [model.jnt_dofadr[model.actuator_trnid[a,0]] for a in self.arm_actuators]
        joints = [model.actuator_trnid[a, 0] for a in range(29)]
        self.lower = np.r_[[-.15, -.12, .62], model.jnt_range[joints, 0]+.001]
        self.upper = np.r_[[.20, .12, .82], model.jnt_range[joints, 1]-.001]

    def solve(self, target):
        targets = np.array([target, self.home_hands[1]])
        prior = self.previous.copy()
        def residual(x):
            d = self.data
            d.qpos[self.vars] = x
            mujoco.mj_kinematics(self.model, d)
            mujoco.mj_comPos(self.model, d)
            return np.r_[30*(d.site_xpos[self.hands]-targets).ravel(),
                         40*(d.xpos[self.feet]-self.fp).ravel(),
                         8*(d.xmat[self.feet].reshape(2,3,3)-self.fr).ravel(),
                         10*(d.xmat[self.wrist].reshape(3,3)-self.rotation).ravel(),
                         30*(d.subtree_com[1,:2]-self.com_xy), .02*(x-prior),
                         .015*(x-self.home[self.vars])]
        fit = least_squares(residual, self.previous, bounds=(self.lower,self.upper),
                            max_nfev=80, ftol=1e-8, xtol=1e-8, gtol=1e-8)
        self.previous = fit.x
        residual(fit.x)
        return self.data.qpos[7:36].copy(), float(np.linalg.norm(self.data.site_xpos[self.hands[0]]-target))

    def nozzle_feedback(self, data, target, offset):
        """Measured Cartesian error changes joint targets, never the simulated pose."""
        jp, jr = np.zeros((3,self.model.nv)), np.zeros((3,self.model.nv))
        mujoco.mj_jacSite(self.model,data,jp,jr,self.hands[0])
        actual = data.xmat[self.wrist].reshape(3,3)
        angular = .5*sum(np.cross(actual[:,j],self.rotation[:,j]) for j in range(3))
        error = np.r_[np.asarray(target)-data.site_xpos[self.hands[0]],.08*angular]
        jac = np.vstack([jp[:,self.arm_dofs],.08*jr[:,self.arm_dofs]])
        delta = .35*jac.T @ np.linalg.solve(jac @ jac.T + .0001*np.eye(6),error)
        result = offset.copy()
        result[self.arm_actuators] = np.clip(result[self.arm_actuators]+np.clip(delta,-.02,.02),-.25,.25)
        return result

    def balance(self, control, data):
        result = control.copy()
        r = data.xmat[self.model.body("pelvis").id].reshape(3,3)
        pitch, roll = np.arctan2(r[0,2],r[2,2]), np.arctan2(-r[1,2],r[2,2])
        e = data.subtree_com[1,:2]-self.com_xy
        correction = np.clip([.6*pitch+.10*data.qvel[4]+1.2*e[0],
                              .6*roll+.10*data.qvel[3]-1.2*e[1]], -.15,.15)
        for side in ("left", "right"):
            result[self.model.actuator(side+"_ankle_pitch_joint").id] += correction[0]
            result[self.model.actuator(side+"_ankle_roll_joint").id] += correction[1]
        return np.clip(result,self.model.actuator_ctrlrange[:,0],self.model.actuator_ctrlrange[:,1])
