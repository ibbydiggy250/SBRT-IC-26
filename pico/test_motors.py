# Wiring check: spins each wheel forward in turn, with the robot on a stand and
# the wheels off the ground.
#
# Running this from Thonny needs USB and the battery connected at the same time.
# Do NOT do that unless whoever built your PCB has confirmed it is safe. The
# README describes a wheel check from the laptop that needs no USB.
#
# For each corner it names, the wheel at that corner should turn the way that
# would move the robot FORWARD. If it turns backwards, or a different wheel
# turns, fix your board's motor pins in robot.py as described there.

import time

import robot

CORNERS = (("fl", "front left"), ("fr", "front right"), ("rl", "rear left"), ("rr", "rear right"))

try:
    for corner, name in CORNERS:
        print("Spinning the", name, "wheel forward")
        robot.motors[corner].set(0.5)
        time.sleep(1.5)
        robot.motors[corner].set(0)
        time.sleep(1)
    print("Done")
finally:
    robot.shutdown()
