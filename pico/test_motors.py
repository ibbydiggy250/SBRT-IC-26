# Wiring check: spins each wheel forward in turn. Open this file on the Pico in
# Thonny and press Run, with the robot on a stand and the wheels off the ground.
#
# For each corner it names, the wheel at that corner should turn the way that
# would move the robot FORWARD. If it turns backwards, or a different wheel
# turns, fix MOTOR_PINS in robot.py as described there.

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
