# Hardware for the IC 2026 PCB: four motors, two servos and the status LED.
# Importing this file sets the pins up; it never touches Wi-Fi.

import machine

# ---------- TUNING ----------
# corner: (IN1 pin, IN2 pin, PWM pin, direction)
# fl = front left, rl = rear left, rr = rear right, fr = front right.
# If a wheel spins backwards, change its direction to -1.
# If a motor is at a different corner than listed, swap the rows' pin numbers.
MOTOR_PINS = {
    "fl": (12, 13, 14, 1),   # M1 on the PCB
    "rl": (10, 11, 15, 1),   # M2
    "rr": (17, 18, 16, 1),   # M3
    "fr": (20, 21, 19, 1),   # M4
}
SERVO_PINS = {"j1": 4, "j2": 5}
STANDBY_PIN = 9              # one pin wakes both motor drivers
LED_PIN = 22                 # LED D1 on the PCB

MOTOR_PWM_HZ = 1000
SERVO_MIN_US = 600           # servo pulse at -1.0
SERVO_MAX_US = 2400          # servo pulse at +1.0

# How much each wheel contributes to (strafe right, forward, turn clockwise).
MECANUM_MIX = {
    "fl": (1, 1, 1),
    "rl": (-1, 1, 1),
    "rr": (1, 1, -1),
    "fr": (-1, 1, -1),
}


def clamp(value):
    return min(max(value, -1.0), 1.0)


class Motor:
    def __init__(self, in1, in2, pwm, direction):
        self.in1 = machine.Pin(in1, machine.Pin.OUT)
        self.in2 = machine.Pin(in2, machine.Pin.OUT)
        self.pwm = machine.PWM(machine.Pin(pwm))
        self.pwm.freq(MOTOR_PWM_HZ)
        self.direction = direction
        self.set(0)

    def set(self, speed):
        """speed is -1.0 (full reverse) to 1.0 (full forward), as the robot sees it."""
        self.speed = clamp(speed)
        drive = self.speed * self.direction
        self.in1.value(1 if drive > 0 else 0)
        self.in2.value(1 if drive < 0 else 0)
        self.pwm.duty_u16(int(abs(drive) * 65535))


class Servo:
    def __init__(self, pin):
        self.pwm = machine.PWM(machine.Pin(pin))
        self.pwm.freq(50)
        self.pulse_us = None   # no pulses are sent until the servo is first used, so it starts limp

    def set(self, position):
        """position is -1.0 to 1.0, spread across the servo's pulse range."""
        fraction = (clamp(position) + 1) / 2
        self.pulse_us = int(SERVO_MIN_US + (SERVO_MAX_US - SERVO_MIN_US) * fraction)
        self.pwm.duty_ns(self.pulse_us * 1000)


standby = machine.Pin(STANDBY_PIN, machine.Pin.OUT)
led = machine.Pin(LED_PIN, machine.Pin.OUT)
led.off()

motors = {corner: Motor(*pins) for corner, pins in MOTOR_PINS.items()}
servos = {name: Servo(pin) for name, pin in SERVO_PINS.items()}
standby.on()


def drive(x, y, rot):
    """x: + strafe right, y: + forward, rot: + turn clockwise. Each is -1.0 to 1.0."""
    x, y, rot = clamp(x), clamp(y), clamp(rot)
    speeds = {corner: wx * x + wy * y + wr * rot for corner, (wx, wy, wr) in MECANUM_MIX.items()}
    # scale everything down together so no wheel is asked for more than full speed
    scale = max(1.0, max(abs(speed) for speed in speeds.values()))
    for corner, speed in speeds.items():
        motors[corner].set(speed / scale)


def stop():
    for motor in motors.values():
        motor.set(0)


def is_moving():
    return any(motor.speed for motor in motors.values())


def shutdown():
    """Stop the wheels and put the motor drivers to sleep."""
    stop()
    standby.off()
    led.off()
