import json
import os
import socket
import sys
import time

# keep reading the controller even when the terminal isn't the focused window
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
import keyboard

#Pico IP address (from Thonny output)
# Original Pico: 192.168.1.25. Test Pico: 192.168.1.183. Newest Pico: 192.168.1.39.
SERVER_IP = "192.168.1.39" # you might be able to use hostname, but its unreliable
SERVER_PORT = 5005
POLL_INTERVAL = 0.02  # how often the controller is read (50 Hz)

KEY_SPEED = 0.6       # driving speed from the keyboard (0 to 1)
KEY_BOOST_SPEED = 1.0 # driving speed while the boost key is held
SERVO_RATE = 1.0      # how fast a held key/button moves a servo: 1.0 = half its travel per second
DEADZONE = 0.1        # stick values smaller than this count as 0 (sticks drift)

LINK_TIMEOUT = 1.0    # no report from the robot for this long = shown as lost
SCREEN_INTERVAL = 0.1 # how often the monitor redraws

# ---------- CONTROLS ----------
# Change keys here; the monitor's labels follow automatically.
# keys and buttons are (positive, negative). axis is (stick axis number, sign).
BOOST_KEY = "shift"
DRIVE = {
    "x":   {"label": "Strafe",  "keys": ("d", "a"),        "axis": (0, 1)},    # left stick, left/right
    "y":   {"label": "Forward", "keys": ("w", "s"),        "axis": (1, -1)},   # left stick, up reads negative
    "rot": {"label": "Turn",    "keys": ("right", "left"), "axis": (2, 1)},    # right stick, left/right
}
SERVOS = {
    "j1": {"label": "Servo 1", "keys": ("o", "k"), "buttons": (1, 0)},   # Xbox B / A
    "j2": {"label": "Servo 2", "keys": ("p", "l"), "buttons": (3, 2)},   # Xbox Y / X
}
WHEELS = {"fl": "front left", "fr": "front right", "rl": "rear left", "rr": "rear right"}


def clamp(value):
    return max(-1.0, min(1.0, value))


def key(name):
    try:
        return 1.0 if keyboard.is_pressed(name) else 0.0
    except Exception:
        return 0.0


def apply_deadzone(value):
    if abs(value) < DEADZONE:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs(value) - DEADZONE) / (1.0 - DEADZONE)


# ---------- inputs -> command ----------

def read_inputs(joy):
    """What the driver is asking for right now, from the keyboard plus the controller if connected.

    Returns one value from -1.0 to 1.0 per control: a speed for each drive
    control, and a direction of travel for each servo.
    """
    speed = KEY_BOOST_SPEED if key(BOOST_KEY) else KEY_SPEED
    inputs = {}
    for field, control in DRIVE.items():
        positive, negative = control["keys"]
        value = (key(positive) - key(negative)) * speed
        if joy is not None:
            axis, sign = control["axis"]
            value += apply_deadzone(sign * joy.get_axis(axis))
        inputs[field] = clamp(value)
    for field, control in SERVOS.items():
        positive, negative = control["keys"]
        value = key(positive) - key(negative)
        if joy is not None:
            forward, back = control["buttons"]
            value += joy.get_button(forward) - joy.get_button(back)
        inputs[field] = clamp(value)
    return inputs


def advance_servos(positions, inputs, dt):
    """Move each servo position (-1 to 1) for dt seconds in the direction its input asks."""
    return {field: clamp(positions[field] + inputs[field] * SERVO_RATE * dt) for field in SERVOS}


def build_command(inputs, servo_positions):
    """The message sent to the robot: drive speeds plus where each servo should be."""
    command = {field: round(inputs[field], 3) for field in DRIVE}
    command.update({field: round(position, 3) for field, position in servo_positions.items()})
    return command


# ---------- link to the robot ----------

REPORT_FIELDS = ("up", "rssi", "temp", "mem", "wheels", "servos", "received", "safety_stops", "t", "age")


def parse_report(data):
    """Return the robot's report as a dict, or None if it isn't a complete one."""
    try:
        report = json.loads(data)
    except ValueError:
        return None
    if not isinstance(report, dict) or report.get("type") != "telemetry":
        return None
    if any(field not in report for field in REPORT_FIELDS):
        return None
    wheels, servos = report["wheels"], report["servos"]
    if not isinstance(wheels, dict) or set(wheels) != set(WHEELS):
        return None
    if not isinstance(servos, dict) or set(servos) != set(SERVOS):
        return None
    return report


class Link:
    """The UDP connection to the robot: sends commands and keeps its newest report."""

    def __init__(self, address):
        self.address = address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.report = None        # newest report from the robot
        self.report_time = None   # when it arrived
        self.ping_ms = None

    def send(self, command, now):
        packet = dict(command, t=int(now * 1000))   # t comes back in the robot's report, giving the ping
        try:
            self.sock.sendto(json.dumps(packet).encode(), self.address)
        except OSError:
            pass

    def poll(self, now):
        """Take in every report the robot has sent since the last call."""
        while True:
            try:
                data, _ = self.sock.recvfrom(2048)
            except OSError:
                return   # nothing waiting (or nothing is listening on the robot yet)
            report = parse_report(data)
            if report is not None:
                self.accept(report, now)

    def accept(self, report, now):
        self.report = report
        self.report_time = now
        try:
            self.ping_ms = max(0.0, now * 1000 - report["t"] - report["age"])
        except TypeError:
            self.ping_ms = None   # the robot hasn't echoed a timestamp yet

    def silence(self, now):
        """Seconds since the robot was last heard from."""
        return now - self.report_time

    def status(self, now):
        if self.report is None:
            return "waiting"
        return "connected" if self.silence(now) < LINK_TIMEOUT else "lost"

    def close(self):
        self.sock.close()


# ---------- monitor (the live status screen in the terminal) ----------

GREEN, RED, YELLOW, DIM, BOLD, RESET = "\x1b[32m", "\x1b[31m", "\x1b[33m", "\x1b[2m", "\x1b[1m", "\x1b[0m"


def bar(value, half=8):
    """A text gauge for a value from -1 to 1, e.g. [........|#####...]"""
    filled = round(abs(clamp(value)) * half)
    left = "#" * filled if value < 0 else ""
    right = "#" * filled if value > 0 else ""
    return "[" + left.rjust(half, ".") + "|" + right.ljust(half, ".") + "]"


def duration(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m {seconds:02d}s" if hours else f"{minutes}m {seconds:02d}s"


def signal_quality(rssi):
    if rssi is None:
        return "unknown"
    if rssi >= -60:
        return f"{rssi} dBm ({GREEN}good{RESET})"
    if rssi >= -72:
        return f"{rssi} dBm ({YELLOW}ok{RESET})"
    return f"{rssi} dBm ({RED}weak{RESET})"


def control_label(control):
    keys = "/".join(name.upper() for name in control["keys"])
    return f"{control['label']} ({keys})"


def render(command, link, now, controller):
    """Build the monitor screen as a list of lines."""
    status = link.status(now)
    report = link.report
    lines = [f"{BOLD}ROBOSIEGE ROBOT MONITOR{RESET}   {DIM}Ctrl+C to quit{RESET}", ""]

    if status == "connected":
        ping = "?" if link.ping_ms is None else f"{link.ping_ms:.0f} ms"
        lines.append(f"  Link        {GREEN}CONNECTED{RESET}   ping {ping}   signal {signal_quality(report['rssi'])}")
    elif status == "waiting":
        lines.append(f"  Link        {RED}NO REPLY{RESET}   is the Pico powered, running main.py, and on the same Wi-Fi?")
    else:
        lines.append(f"  Link        {RED}LOST{RESET}   last heard from the robot {link.silence(now):.0f}s ago")
    lines.append(f"  Robot       {link.address[0]}:{link.address[1]}")
    lines.append(f"  Controller  {controller}")

    lines += ["", f"{BOLD}YOU ARE SENDING{RESET}"]
    for field, control in list(DRIVE.items()) + list(SERVOS.items()):
        lines.append(f"  {control_label(control):<20} {command[field]:+.2f}  {bar(command[field])}")

    lines += ["", f"{BOLD}ROBOT REPORTS{RESET}"]
    if status != "connected":
        lines.append(f"  {DIM}waiting for the robot...{RESET}")
        return lines

    wheels = report["wheels"]
    moving = f"{GREEN}DRIVING{RESET}" if any(wheels.values()) else "stopped"
    temp, mem = report["temp"], report["mem"]
    lines += [
        f"  State          {moving}",
        f"  Wheels         front left {wheels['fl']:+.2f}   front right {wheels['fr']:+.2f}",
        f"                 rear left  {wheels['rl']:+.2f}   rear right  {wheels['rr']:+.2f}",
    ]
    for field, control in SERVOS.items():
        pulse = report["servos"][field]
        lines.append(f"  {control['label']:<14} {'not used yet' if pulse is None else f'{pulse} us'}")
    lines += [
        f"  Powered on     {duration(report['up'])}",
        f"  Chip temp      {'?' if temp is None else f'{temp:.1f} C'}",
        f"  Free memory    {'?' if mem is None else f'{mem // 1024} KB'}",
        f"  Commands in    {report['received']}",
        f"  Safety stops   {report['safety_stops']}  {DIM}(times it stopped because the laptop went quiet){RESET}",
    ]
    return lines


def draw(lines):
    # go to the top-left, rewrite every line in place, then clear whatever is left below
    sys.stdout.write("\x1b[H" + "".join(line + "\x1b[K\n" for line in lines) + "\x1b[J")
    sys.stdout.flush()


# ---------- main loop ----------

def track_controller(joy, description):
    """Handle controllers being plugged in or removed. Returns (joystick or None, description)."""
    for event in pygame.event.get():
        if event.type == pygame.JOYDEVICEADDED and joy is None:
            joy = pygame.joystick.Joystick(event.device_index)
            description = f"keyboard + {joy.get_name()}"
        elif event.type == pygame.JOYDEVICEREMOVED and joy is not None:
            if event.instance_id == joy.get_instance_id():
                joy = None
                description = "keyboard (controller disconnected)"
    return joy, description


def main():
    if not SERVER_IP:
        sys.exit("Set SERVER_IP at the top of this file to the IP the Pico prints in Thonny.")

    pygame.init()
    pygame.joystick.init()
    link = Link((SERVER_IP, SERVER_PORT))

    joy = None
    controller = "keyboard (plug in an Xbox controller to use it too)"
    servo_positions = {field: 0.0 for field in SERVOS}   # servos stay where you leave them
    last_loop = time.monotonic()
    next_draw = 0.0

    os.system("")                           # switches on colour/cursor codes in older Windows terminals
    sys.stdout.write("\x1b[2J\x1b[?25l")    # clear the screen, hide the cursor

    try:
        while True:
            now = time.monotonic()
            dt, last_loop = now - last_loop, now

            joy, controller = track_controller(joy, controller)
            inputs = read_inputs(joy)
            servo_positions = advance_servos(servo_positions, inputs, dt)
            command = build_command(inputs, servo_positions)

            link.send(command, now)
            link.poll(now)

            if now >= next_draw:
                draw(render(command, link, now, controller))
                next_draw = now + SCREEN_INTERVAL

            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        # tell the robot to stop now instead of waiting for its timeout
        stop = build_command({field: 0.0 for field in DRIVE}, servo_positions)
        for _ in range(3):
            link.send(stop, time.monotonic())
        link.close()
        pygame.quit()
        sys.stdout.write("\x1b[?25h\n")   # show the cursor again
        print("Stopped.")


if __name__ == "__main__":
    main()
