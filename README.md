# IC27-RoboSiege-Software

Officially distributed software for SBRT's internal competition for the 2027 season — RoboSiege.

This branch fills in the starter code: mecanum driving, two servos, a safety stop, and a live status monitor on the laptop. This README covers everything needed to get a robot driving from a blank Pico.

## How it fits together

- **`/pico`** runs on the Raspberry Pi Pico W. It joins Wi-Fi, listens for commands, drives the motors and servos, and reports back what it is doing.
- **`/laptop`** runs on your computer. It reads the keyboard (and an Xbox controller if one is plugged in), sends commands to the Pico, and shows the robot's status in the terminal.

The two talk over Wi-Fi, so **the laptop and the Pico must be on the same network.** The laptop finds the Pico by its IP address, which you copy from Thonny into `laptop/main.py` (step 5 below).

| File | Runs on | What it does |
|---|---|---|
| `pico/main.py` | Pico | Wi-Fi, receiving commands, safety stop, status reports. Starts by itself at power-up. |
| `pico/robot.py` | Pico | Pin numbers, motor directions, servo range. |
| `pico/config.json` | Pico | Wi-Fi name, Wi-Fi password and the robot's hostname. |
| `pico/test_motors.py` | Pico | Optional wiring check. Read its header before using it. |
| `laptop/main.py` | Laptop | Controls, the Pico's IP address, and the status monitor. |

## Safety rules

One Pico burned out on battery power during bring-up, and another developed a fault. The cause was never pinned down, so treat these as rules:

1. **Never have the USB cable and the battery connected at the same time.** Take the Pico off the PCB to upload code.
2. **Disconnect the battery before** seating or removing the Pico, plugging servos in or out, or touching any wiring.
3. **Check the Pico's orientation** every time it goes back in the socket: USB port facing the same way as before, no pins hanging off either end.
4. **Keep a finger on the Pico for the first ten seconds** after connecting the battery. Warm is fine. Hot means disconnect immediately.
5. **Put the robot on a stand**, wheels off the ground, whenever you test.
6. **The laptop reads keys even when another window is in front.** While the controller is running, typing anywhere drives the robot. On Windows, the screenshot shortcut Win+Shift+S commands full-speed reverse (Shift is boost, S is reverse).

## Requirements

You need Python, Thonny, and a code editor such as VSCode.

### VSCode Installation

Download and install Visual Studio Code from [https://code.visualstudio.com/](https://code.visualstudio.com/).

Once installed, open VSCode and install the **Python** extension by Microsoft from the Extensions tab.

### Python Installation

Download Python from [https://www.python.org/downloads/](https://www.python.org/downloads/).

**Windows:**

- Run the Python installer.
- If the installer offers an **Add Python to PATH** option, enable it. This allows you to run Python from any terminal.
- If using the Python Install Manager, follow its prompts to make Python commands available.
- Verify installation by opening a new terminal and running `python --version` or `py --version`.

**Mac:**

- Download and run the Python installer.
- Open Terminal and verify installation with `python3 --version`.
- Python is generally accessible through `python3` rather than `python`. If the command is not found, ensure the Python installation's executable directory is included in your shell's `PATH`.

### Thonny Installation

Download Thonny from [https://thonny.org/](https://thonny.org/) and install the appropriate version for your operating system. Thonny is used to install MicroPython on the Pico and to upload and run its code.

### A USB data cable

You need a micro-USB cable that carries data. Many cables only carry power, and with one of those the Pico never shows up on the computer. Use a cable you have transferred files with before.

## Setting up a Pico, step by step

Do steps 1 to 7 with the **Pico off the PCB**, connected only by USB.

### 1. Install MicroPython (BOOTSEL)

A new Pico is blank and needs MicroPython installed once.

1. Unplug the Pico from USB.
2. Hold down the white **BOOTSEL** button on the Pico.
3. While still holding it, plug the USB cable into the computer. Then let go.
4. The Pico appears on the computer as a drive named `RPI-RP2`. That means it is in install mode.
5. In Thonny, go to **Run → Configure interpreter**.
6. Choose **MicroPython (Raspberry Pi Pico)** as the interpreter.
7. Click **Install or update MicroPython** in that window.
8. Fill in the install window:
   - **Target volume:** `RPI-RP2`
   - **MicroPython family:** `RP2`, if it asks
   - **Variant:** `Raspberry Pi • Pico W / Pico WH`
   - **Version:** the latest one offered
9. Click **Install**, wait for it to say Done, and close the window.

The variant matters. The plain "Pico" variant has no Wi-Fi support, and `main.py` will fail with an error about `network`.

After this, plug the Pico in normally. BOOTSEL is only for installing MicroPython.

A Pico W has no power light. Its LED is controlled by code, so a blank Pico, or one in BOOTSEL mode, stays dark even when it is working.

### 2. Connect Thonny to the Pico

1. Go to **Run → Configure interpreter** again if it is not still open.
2. Interpreter: **MicroPython (Raspberry Pi Pico)**.
3. Port: leave it on automatic detection, or pick the entry for your Pico (a `COM` port on Windows).
4. Click OK.
5. Click the red **STOP** button in the toolbar (or press Ctrl+F2). This makes Thonny connect.

The Shell at the bottom should show a line starting `MicroPython` and mentioning `Pico W`, followed by a `>>>` prompt. You can also change the interpreter and port by clicking the text in the bottom-right corner of the Thonny window.

### 3. Set the hostname

Before uploading, open `pico/config.json` on your computer and change `HOSTNAME` to something unique to your team. `SSID` and `PASSWORD` are the Wi-Fi network the Pico joins; change them only if you are testing on a different network. The Pico W can only use 2.4 GHz Wi-Fi.

### 4. Upload the code

1. In Thonny, turn on **View → Files**. The top pane shows your computer, the bottom pane shows the Pico.
2. In the top pane, go to this repository's `pico` folder.
3. Select `config.json`, `main.py`, `robot.py` and `test_motors.py`.
4. Right-click and choose **Upload to /**. Say yes if asked to overwrite.
5. Check that all four files appear in the Pico pane at the top level, not inside a folder.

Whenever you change a file in `pico`, upload that file again. If Thonny has the Pico's old copy open in a tab (the name is shown in square brackets, such as `[ main.py ]`), close that tab and reopen the file from the Pico pane, or you will run the old version.

`main.py` and `robot.py` must match. If you update one, upload both.

### 5. Get the IP address and put it in the laptop code

1. In the Pico pane, double-click `main.py` to open it.
2. Press the green **Run** button (or F5).
3. The Shell prints something like this:

   ```
   WIFI CONNECTED
   IP:('192.168.1.50', '255.255.255.0')
   hostname: yourteam
   UDP server listening on 5005
   ```

4. Copy the first address on the `IP:` line.
5. On your computer, open `laptop/main.py` and set `SERVER_IP` near the top:

   ```python
   SERVER_IP = "192.168.1.50"
   ```

If it never prints `WIFI CONNECTED`, the Pico cannot find or join the network in `config.json`. It keeps waiting forever and does not give an error.

`laptop/main.py` stays on your computer. It is never uploaded to the Pico.

The IP address belongs to one Pico on one network. A different Pico gets a different address, and the router can hand out a new one after a restart. If the laptop cannot reach the robot, run `main.py` in Thonny again and check the `IP:` line first.

### 6. Install the laptop packages

The laptop side needs `pygame` (controller support) and `keyboard` (reading keys). Open a terminal in the repository folder and run:

```bash
cd laptop
python -m pip install -r requirements.txt
```

On Mac, use `python3 -m pip`.

**Optional:** to keep these packages separate from your other Python projects, create a virtual environment first with `python -m venv .venv`, then activate it with `.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on Mac.

This has only been run on Windows. On Mac and Linux, the `keyboard` package normally needs the program to be run with administrator rights (`sudo`).

### 7. Run the controller

1. Connect the laptop to the **same Wi-Fi network as the Pico**. You will probably lose internet while on the robot network.
2. With `main.py` still running on the Pico in Thonny, open a terminal in the `laptop` folder and run:

   ```bash
   python main.py
   ```

3. The monitor appears. The `Link` line tells you the state:
   - **CONNECTED:** the robot is answering. You will also see ping and Wi-Fi signal strength.
   - **NO REPLY:** nothing has come back from the robot yet. See Troubleshooting.
   - **LOST:** it was connected and the robot has stopped answering.
4. Hold W. Under ROBOT REPORTS, all four wheels should show `+0.60`, even with no motors attached. This proves the whole chain works before the Pico goes on the robot.
5. Press **Ctrl+C** in the terminal to quit.

### 8. Move to the robot

1. Press Ctrl+C in the terminal and STOP in Thonny, then unplug the USB cable.
2. With the battery disconnected, seat the Pico in the PCB the right way round.
3. Put the robot on a stand.
4. Connect the battery and make sure the robot's power switch is on.
5. Wait about ten seconds for Wi-Fi. `main.py` starts by itself at power-up; nothing needs to be pressed. The Pico's own LED turns on when the program starts.
6. Run `python main.py` in the `laptop` folder again and wait for CONNECTED.

Check `Chip temp` on the monitor. It should read roughly 25 to 40 C. A wild value such as 200 C may mean the Pico's power supply is wrong on that board; disconnect the battery and investigate.

## Controls

| Action | Keyboard | Xbox controller |
|---|---|---|
| Forward / backward | W / S | Left stick up / down |
| Strafe right / left | D / A | Left stick right / left |
| Turn right / left | Right arrow / Left arrow | Right stick right / left |
| Full speed (boost) | Hold Shift | Push the stick further |
| Servo 1 | O / K | B / A |
| Servo 2 | P / L | Y / X |
| Quit | Ctrl+C | |

- Keyboard driving runs at 60% speed, or 100% while Shift is held.
- A held servo key moves the servo gradually, and it stays where you leave it. End to end takes about two seconds.
- Both servos move to their centre position when the controller starts. Make sure that is safe for your mechanism.
- If the laptop stops sending for half a second (program closed, Wi-Fi dropped), the robot stops its wheels by itself.

To change keys, speeds or the servo rate, edit the settings and the CONTROLS tables near the top of `laptop/main.py`. The monitor's labels follow automatically.

## Checking wheel directions

Motor directions depend on how each motor is wired, so every robot needs this check once. Do it on a stand, driving from the laptop, so no USB cable is involved.

The code assumes this layout, seen from above with the front of the robot at the top:

```
Motor 1 (front left)     Motor 4 (front right)
Motor 2 (rear left)      Motor 3 (rear right)
```

1. **Hold W.** All four wheels should turn forward. For each wheel that turns backward, open `pico/robot.py`, find that wheel's row (the ones in use look like the example below), and change its last number from `1` to `-1` (or back):

   ```python
   "fl": (4, 3, 2, -1),     # M1
   ```

   The rows are `fl` front left, `rl` rear left, `rr` rear right, `fr` front right.

2. **Upload `robot.py` again** (Pico off the board) and re-test W.

3. **Hold D (strafe right).** Front left and rear right should turn forward; front right and rear left backward. A is the opposite.

4. **Hold Right arrow (turn right).** Both left wheels forward, both right wheels backward.

If W is correct but step 3 or 4 is wrong, two motors are plugged into each other's corners: swap the pin numbers of those two rows. If the wheels match but the robot will not slide sideways on the ground, the mecanum wheels are mounted in the wrong positions; seen from above, the rollers should form an X.

## What has and has not been tested

- **Driving:** checked in all directions on one robot, and the wheel directions are tuned for that robot. Another robot may need the wheel-direction check above.
- **Servos:** never confirmed working. The servo pins (GP28 and GP0) come from the organisers' code and have not been verified.
- **Xbox controller:** written but not tested with a real controller.

## Troubleshooting

**The Pico does not show up at all (no `RPI-RP2` drive, nothing in Thonny).**
Almost always a power-only USB cable. Try another cable. The Pico W has no power light, so a dark board is normal.

**Thonny says "Unable to connect" or "port not found".**
This often appears right after installing MicroPython, while the Pico restarts. Press STOP. If that fails, unplug the Pico, plug it back in without holding BOOTSEL, wait a few seconds and press STOP again. Close any other program using the port, such as a second Thonny window.

**`main.py` never prints `WIFI CONNECTED`.**
The network in `config.json` is out of range, misspelled, has the wrong password, or is 5 GHz only.

**`ModuleNotFoundError: No module named 'pygame'` after installing it.**
The computer has more than one Python, and `pip` installed into a different one than `python` runs. Always install with `python -m pip install -r requirements.txt` so both use the same one. On Windows you can also pick a version explicitly, for example `py -3.11 -m pip install -r requirements.txt` and then `py -3.11 main.py`.

**The monitor says NO REPLY.**
Check these in order:
1. The laptop is on the same Wi-Fi network as the Pico, not a campus or home network.
2. `SERVER_IP` matches the `IP:` line the Pico printed. It changes between Picos and can change after a restart.
3. The Pico has power and `main.py` is running.

**`AttributeError: 'NoneType' object has no attribute 'on'` in Thonny.**
The Pico has a new `robot.py` with an old `main.py`. Upload both from the `pico` folder, and close any stale `[ main.py ]` tab.

**The monitor shows DRIVING but nothing moves.**
The commands are arriving, so this is power or wiring. Check the robot's power switch, the battery charge, and that the Pico is seated correctly. Motors run from battery voltage and servos from a separate 5 V supply, so one can work without the other.

**Servos do not move.**
If the `Servo` numbers under ROBOT REPORTS change when you hold the keys, the Pico is sending the signal. With a multimeter on DC volts, measure between the power and ground pins of a servo header with the battery on. It should read about 5 V.

**The wheels move when nobody is pressing a driving key.**
Keys are read from the whole computer, not just the terminal. Something else you typed, or a shortcut such as Win+Shift+S, contained a driving key.

**The Pico gets hot.**
Disconnect everything immediately. To test it afterwards, plug it into USB alone, off the board. If it heats up by itself, it is damaged. Before fitting another Pico, measure the empty socket with the battery on: the VBUS and VSYS positions (pins 40 and 39) should read no more than about 5.5 V, and the 3V3 position (pin 36) about 0 V.
