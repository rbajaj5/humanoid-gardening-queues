"""CUDA ballistic water parcels: gravity, finite source, measured capture plane.

Not CFD: no inter-particle pressure, surface tension, leaf collisions, or soil.
Each parcel is one millilitre. It is captured only on crossing a pot's soil plane.
"""
import numpy as np
import warp as wp
from physical_garden.model import POTS, SOIL_Z, POT_RADIUS


@wp.kernel
def emit(p: wp.array(dtype=wp.vec3), v: wp.array(dtype=wp.vec3), active: wp.array(dtype=wp.int32),
         index: int, origin: wp.vec3, velocity: wp.vec3):
    p[index] = origin
    v[index] = velocity
    active[index] = 1


@wp.kernel
def advance(p: wp.array(dtype=wp.vec3), v: wp.array(dtype=wp.vec3), active: wp.array(dtype=wp.int32),
            pots: wp.array(dtype=wp.vec3), landed: wp.array(dtype=wp.int32), missed: wp.array(dtype=wp.int32),
            dt: float, radius: float, plane: float):
    i = wp.tid()
    if active[i] == 1:
        old = p[i]
        velocity = v[i] + wp.vec3(0.0, 0.0, -9.81)*dt
        new = old + velocity*dt
        if old[2] > plane and new[2] <= plane:
            fraction = (old[2]-plane)/(old[2]-new[2])
            at = old + fraction*(new-old)
            hit = int(-1)
            for j in range(3):
                delta = at-pots[j]
                if delta[0]*delta[0]+delta[1]*delta[1] <= radius*radius:
                    hit = j
            if hit >= 0:
                wp.atomic_add(landed, hit, 1)
            else:
                wp.atomic_add(missed, 0, 1)
            active[i] = 0
        p[i] = new
        v[i] = velocity


class Water:
    def __init__(self, capacity=500):
        self.capacity, self.emitted = capacity, 0
        self.p = wp.zeros(capacity,dtype=wp.vec3,device="cuda:0")
        self.v = wp.zeros(capacity,dtype=wp.vec3,device="cuda:0")
        self.active = wp.zeros(capacity,dtype=wp.int32,device="cuda:0")
        self.pots = wp.array(np.c_[POTS,np.full(3,SOIL_Z)].astype(np.float32),dtype=wp.vec3,device="cuda:0")
        self.landed = wp.zeros(3,dtype=wp.int32,device="cuda:0")
        self.missed = wp.zeros(1,dtype=wp.int32,device="cuda:0")

    def step(self, origin=None, velocity=None):
        if origin is not None and self.emitted < self.capacity:
            wp.launch(emit,dim=1,inputs=[self.p,self.v,self.active,self.emitted,
                      wp.vec3(*origin),wp.vec3(*velocity)],device="cuda:0")
            self.emitted += 1
        for _ in range(4):
            wp.launch(advance,dim=self.capacity,inputs=[self.p,self.v,self.active,self.pots,
                      self.landed,self.missed,.01,POT_RADIUS,SOIL_Z],device="cuda:0")

    def snapshot(self):
        active = self.active.numpy().astype(bool)
        return self.landed.numpy().astype(int), int(self.missed.numpy()[0]), self.p.numpy()[active].copy()
