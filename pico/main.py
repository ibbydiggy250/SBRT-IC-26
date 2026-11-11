# Pico W firmware: joins Wi-Fi, takes drive commands from the laptop over UDP,
# and reports back what the robot is doing. Runs automatically at power-up.
# Pins and tuning live in robot.py.

import errno
import gc
import json
import socket
import time

import machine
import network

import robot

PORT = 5005
COMMAND_TIMEOUT_MS = 500      # stop driving if the laptop goes quiet for this long
TELEMETRY_INTERVAL_MS = 200   # how often the robot reports back to the laptop's monitor
TELEMETRY_IDLE_MS = 3000      # stop reporting once the laptop has been gone this long

try:
    temp_sensor = machine.ADC(4)   # the Pico's built-in chip temperature sensor
except Exception:
    temp_sensor = None


def read_temp():
    if temp_sensor is None:
        return None
    volts = temp_sensor.read_u16() * 3.3 / 65535
    return round(27 - (volts - 0.706) / 0.001721, 1)


def wifi_signal(wlan):
    try:
        return wlan.status("rssi")
    except Exception:
        return None


def number(packet, key):
    """Read a numeric field from a command, treating missing or junk values as 0."""
    try:
        return float(packet.get(key, 0))
    except (TypeError, ValueError):
        return 0.0


def connect_wifi():
    # WLAN INIT (the organisers' code; settings come from config.json)
    with open("config.json", "r") as f:
        config = json.load(f)

    network.hostname(config["HOSTNAME"])

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.scan()
    wlan.connect(config["SSID"], config["PASSWORD"])
    while not wlan.isconnected():
        machine.idle()
    print("WIFI CONNECTED")
    print(f"IP:{wlan.ipconfig('addr4')}")
    wlan.config(hostname=config["HOSTNAME"]) # change HOSTNAME in config.json to your robots name - itll show on WiFi
    print(f"hostname: {wlan.config('hostname')}")
    return wlan


def newest_command(sock):
    """Read everything waiting on the socket and return the newest (command, sender), or None.

    Older commands are dropped on purpose, so the robot never lags behind the driver.
    """
    newest = None
    while True:
        try:
            data, addr = sock.recvfrom(1024)
        except OSError as e:
            if e.args[0] != errno.EAGAIN:
                raise
            return newest
        try:
            packet = json.loads(data)
        except ValueError:
            continue   # ignore anything that isn't valid JSON
        if isinstance(packet, dict):
            newest = (packet, addr)


class Controller:
    """Applies the laptop's commands to the robot and keeps the numbers its monitor shows."""

    def __init__(self):
        self.laptop = None            # where the newest command came from; reports go back there
        self.last_rx = time.ticks_ms()
        self.echo = None              # the laptop's timestamp from the newest command, for measuring ping
        self.received = 0
        self.safety_stops = 0

    def command(self, packet, addr):
        robot.drive(number(packet, "x"), number(packet, "y"), number(packet, "rot"))
        # only move a servo when the laptop mentions it, so it stays limp until first used
        for name, servo in robot.servos.items():
            if name in packet:
                servo.set(number(packet, name))

        self.laptop = addr
        self.last_rx = time.ticks_ms()
        self.echo = packet.get("t")
        self.received += 1

    def quiet_ms(self):
        return time.ticks_diff(time.ticks_ms(), self.last_rx)

    def check_timeout(self):
        """Stop if the laptop has gone quiet, so a dropped link can't leave the robot driving."""
        if robot.is_moving() and self.quiet_ms() > COMMAND_TIMEOUT_MS:
            print("No commands from laptop, stopping")
            robot.stop()
            self.safety_stops += 1

    def report(self, rssi):
        """Everything the laptop's monitor shows about the robot."""
        return {
            "type": "telemetry",
            "up": time.ticks_ms() // 1000,
            "rssi": rssi,
            "temp": read_temp(),
            "mem": gc.mem_free(),
            "wheels": {corner: round(motor.speed, 2) for corner, motor in robot.motors.items()},
            "servos": {name: servo.pulse_us for name, servo in robot.servos.items()},
            "received": self.received,
            "safety_stops": self.safety_stops,
            "t": self.echo,
            "age": self.quiet_ms(),
        }


def main():
    machine.Pin("LED", machine.Pin.OUT).on()   # onboard LED: the program is running

    wlan = connect_wifi()
    robot.led.on()                             # PCB LED: Wi-Fi is up

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.setblocking(False)
    print("UDP server listening on", PORT)

    controller = Controller()
    next_report = time.ticks_ms()
    try:
        while True:
            newest = newest_command(sock)
            if newest is not None:
                controller.command(*newest)
            else:
                controller.check_timeout()

            now = time.ticks_ms()
            report_due = time.ticks_diff(now, next_report) >= 0
            if controller.laptop is not None and report_due and controller.quiet_ms() < TELEMETRY_IDLE_MS:
                next_report = time.ticks_add(now, TELEMETRY_INTERVAL_MS)
                try:
                    sock.sendto(json.dumps(controller.report(wifi_signal(wlan))).encode(), controller.laptop)
                except OSError:
                    pass   # a dropped report doesn't matter, the next one is 200 ms away

            time.sleep_ms(5)
    finally:
        sock.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        # whatever ends the program (Stop in Thonny, an error), don't leave the wheels spinning
        robot.shutdown()
