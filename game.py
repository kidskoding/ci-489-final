from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import queue
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import pygame

from orbit import Orbit, Vec2


WIDTH = 1024
HEIGHT = 579
FPS = 60
BACKGROUND = (6, 24, 34)
PANEL = (8, 43, 56)
PANEL_LIGHT = (113, 232, 235)
TEXT = (244, 251, 253)
MUTED = (132, 170, 178)
ACCENT = (28, 235, 244)
ORBIT = (168, 191, 206)
MEASURE = (255, 64, 170)
PLANET = (70, 167, 255)
STAR = (252, 196, 25)
PERI = (76, 217, 100)
APO = (255, 149, 79)
FOCUS = (196, 181, 253)
SHIP_WALL = (87, 110, 182)
SHIP_SEAM = (255, 65, 169)
MODAL = (31, 220, 225)
MODAL_TEXT = (10, 43, 52)
BUTTON = (83, 178, 185)
DEFAULT_PORT = 3000
DISCOVERY_PORT = 48901
JOIN_CODE = "CI-489-DEMO"
RELAY_HOST = "ci-489-final.onrender.com"


ASSET_ROOT = Path(__file__).resolve().parent / "assets"
EARTH_TEXTURE = ASSET_ROOT / "planets/Earth_4k.png"
MILKY_WAY_TEXTURE = ASSET_ROOT / "space/milkyway_2048.png"

UI_ASSETS = ASSET_ROOT / "ui"
SHIP_ASSETS = ASSET_ROOT / "ship"
PLAYER_ASSETS = ASSET_ROOT / "player"

SHIP_MAP_PATH = SHIP_ASSETS / "map.png"
PROMPT_PATH = UI_ASSETS / "prompt.png"
PLAYER_SIDE_PATH = PLAYER_ASSETS / "side"
PLAYER_IDLE_PATH = PLAYER_SIDE_PATH / "01.png"
PANEL_BG_PATH = UI_ASSETS / "panel_bg.png"
FRAME_BG_PATH = UI_ASSETS / "frame_bg.png"
DIALOG_BG_PATH = UI_ASSETS / "dialog_bg.png"
TASK_BG_PATH = UI_ASSETS / "task_bg.png"
KEPLER_PANEL_PATH = UI_ASSETS / "kepler_panel.png"


@dataclass
class Body:
    name: str
    pos: Vec2
    radius: int
    color: tuple[int, int, int]


@dataclass
class Measurement:
    start: str
    end: str
    distance: float
    t: float
    visible: bool = True


@dataclass
class Terminal:
    name: str
    rect: pygame.Rect
    activity: str
    description: str
    color: tuple[int, int, int]


@dataclass
class CrewMember:
    name: str
    role: str
    color: tuple[int, int, int]
    pos: tuple[int, int]
    joined: bool = False
    ready: bool = False


@dataclass(frozen=True)
class LessonMode:
    key: str
    title: str
    law: str
    objective: str
    description: str


@dataclass
class AreaCapture:
    start_t: float
    end_t: float
    area: float
    label: str


@dataclass(frozen=True)
class OrbitPreset:
    name: str
    semi_major_axis: float
    period: float


@dataclass(frozen=True)
class TutorialStep:
    message: str
    event: str
    target: str | None


TUTORIAL_STEPS: list[TutorialStep] = [
    TutorialStep("Click the Red Dwarf star to select it.", "star", "Red Dwarf"),
    TutorialStep("Now click Aphelion — the farthest orbit point — to measure the star's distance.", "aphelion_measure", "Aphelion"),
    TutorialStep("Red Dwarf is pre-selected. Now click Perihelion — the nearest point.", "perihelion_measure", "Perihelion"),
    TutorialStep("Perihelion is much closer. The star sits at a focus, not the center — Kepler's First Law! Click anywhere to continue.", "continue", None),
    TutorialStep("Press Space to pause and resume the orbit.", "pause", None),
    TutorialStep("Press + or − to zoom in and out.", "zoom", None),
    TutorialStep("All done! Click the nav icon to return to the ship.", "nav", "nav"),
]


LESSON_MODES = {
    "law1": LessonMode(
        "law1",
        "Orbit Shape Lab",
        "Kepler's First Law",
        "Change the orbit until the star sits at one focus, not the center.",
        "Planet paths are ellipses. The star is at a focus, so higher eccentricity pushes the empty focus farther away.",
    ),
    "law2": LessonMode(
        "law2",
        "Equal Area Sweep",
        "Kepler's Second Law",
        "Capture two equal-time sweeps and compare the swept areas.",
        "A line from the star to the planet sweeps out equal areas in equal times, even when the planet moves faster near perihelion.",
    ),
    "law3": LessonMode(
        "law3",
        "Period Ratio Lab",
        "Kepler's Third Law",
        "Compare worlds and find the constant T^2 / a^3 relationship.",
        "The square of a planet's orbital period scales with the cube of its semi-major axis.",
    ),
    "tutorial": LessonMode(
        "tutorial",
        "Interactive Tutorial",
        "Mission Training",
        "Follow the highlighted prompts to learn the simulator.",
        "Practice opening modes, selecting bodies, recording a measurement, and returning to the ship.",
    ),
}

ORBIT_PRESETS = [
    OrbitPreset("Mercury", 0.39, 0.24),
    OrbitPreset("Earth", 1.00, 1.00),
    OrbitPreset("Mars", 1.52, 1.88),
    OrbitPreset("Jupiter", 5.20, 11.86),
]


class NetworkSession:
    def __init__(self, mode: str = "solo", host: str = "localhost:3000", port: int = DEFAULT_PORT, name: str = "Player") -> None:
        self.mode = mode
        self.host = host
        self.port = port
        self.name = name
        self.room = JOIN_CODE
        self.inbox = queue.Queue()
        self.running = False
        self.status = "Solo"
        self.ws = None
        self.task = None
        self.player_names = [name]

        if mode in ["host", "join"]:
            self.start()

    def start(self) -> None:
        if self.mode == "solo" or self.running:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.status = "Waiting for event loop"
            return
        else:
            self.running = True
            self.status = "Connecting..."
            self.task = loop.create_task(self._ws_loop(self.host))

    @property
    def connected(self) -> bool:
        return self.ws is not None and self.running

    def send(self, message: dict) -> None:
        if self.mode == "solo" or not self.ws:
            return
        payload = json.dumps(message)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.ws.send(payload))

    async def _ws_loop(self, host: str) -> None:
        import websockets
        host = self.normalize_host(host)

        # In browser/pygbag, allow a relay query param to override the configured host.
        # If no host was configured, fall back to same-origin for self-hosted builds.
        try:
            import platform
            params = platform.window.URLSearchParams.new(platform.window.location.search)
            relay = params.get("relay")
            if relay:
                host = self.normalize_host(str(relay))
            window_host = platform.window.location.host
            if not relay and not host and window_host:
                host = self.normalize_host(str(window_host))
        except:
            pass

        uri = f"ws://{host}"
        # If running on HTTPS, use wss://
        try:
            import platform
            if platform.window.location.protocol == "https:":
                uri = f"wss://{host}"
        except:
            pass
        
        try:
            async with websockets.connect(uri) as websocket:
                self.ws = websocket
                self.status = "Connected"
                # Join the room
                await self.ws.send(json.dumps({"type": "join", "room": self.room}))
                # Identify self
                await self.ws.send(json.dumps({"type": "hello", "name": self.name}))
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        self._handle_message(data)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self.status = f"Error: {e}"
            self.running = False

    def normalize_host(self, host: str) -> str:
        clean = host.strip()
        if not clean:
            return clean
        if clean.startswith("ws://"):
            clean = clean.removeprefix("ws://")
        elif clean.startswith("wss://"):
            clean = clean.removeprefix("wss://")
        clean = clean.rstrip("/")
        if ":" not in clean:
            is_ipv4 = clean.replace(".", "").isdigit()
            clean = clean if "." in clean and not is_ipv4 else f"{clean}:{self.port}"
        return clean

    def _handle_message(self, message: dict) -> None:
        m_type = message.get("type")
        if m_type == "hello_ack":
            name = str(message.get("name", self.name))
            self.name = name
            if self.player_names:
                self.player_names = [name if existing == self.player_names[0] else existing for existing in self.player_names]
            else:
                self.player_names = [name]
            self.inbox.put({"type": "hello_ack", "name": name})
            return
        if m_type == "hello":
            name = message.get("name", "Unknown")
            if name not in self.player_names:
                self.player_names.append(name)
            self.inbox.put({"type": "players", "players": self.player_names[:4]})
        elif m_type == "players":
            self.player_names = message.get("players", [self.name])
            self.inbox.put(message)
        else:
            self.inbox.put(message)

    def poll(self) -> list[dict]:
        messages = []
        while True:
            try:
                messages.append(self.inbox.get_nowait())
            except queue.Empty:
                return messages

    def close(self) -> None:
        self.running = False
        if self.task is not None:
            self.task.cancel()
            self.task = None


class LocalRelayServer:
    def __init__(self, port: int = DEFAULT_PORT, join_code: str = JOIN_CODE) -> None:
        self.port = port
        self.join_code = join_code
        self.rooms: dict[str, set] = {}
        self.ready = threading.Event()
        self.stop_requested = threading.Event()
        self.thread: threading.Thread | None = None
        self.error: str | None = None

    def start(self) -> bool:
        if is_browser_runtime():
            self.error = "Local relay is unavailable in browser builds."
            return False
        if self.thread and self.thread.is_alive():
            return True
        self.stop_requested.clear()
        self.ready.clear()
        self.error = None
        self.thread = threading.Thread(target=self._run_thread, daemon=True)
        self.thread.start()
        self.ready.wait(1.5)
        return self.error is None and self.ready.is_set()

    def stop(self) -> None:
        self.stop_requested.set()

    def _run_thread(self) -> None:
        try:
            asyncio.run(self._serve())
        except Exception as exc:
            self.error = str(exc)
            self.ready.set()

    def room_players(self, room_code: str) -> list[str]:
        if room_code not in self.rooms:
            return []
        return [
            ws.player_name
            for ws in self.rooms[room_code]
            if getattr(ws, "player_name", None)
        ]

    def unique_player_name(self, room_code: str, requested: str, ws) -> str:
        base = (requested or "Player").strip() or "Player"
        existing = set(self.room_players(room_code)) - {getattr(ws, "player_name", None)}
        max_length = 24
        first_choice = base[:max_length]
        if first_choice not in existing:
            return first_choice

        suffix = 2
        while True:
            suffix_text = f" {suffix}"
            candidate = f"{base[:max_length - len(suffix_text)]}{suffix_text}"
            if candidate not in existing:
                return candidate
            suffix += 1

    async def broadcast(self, room_code: str, message: dict, exclude=None) -> None:
        if room_code not in self.rooms:
            return
        payload = json.dumps(message)
        targets = [ws for ws in self.rooms[room_code] if ws is not exclude]
        if targets:
            await asyncio.gather(*[ws.send(payload) for ws in targets], return_exceptions=True)

    async def broadcast_roster(self, room_code: str) -> None:
        await self.broadcast(room_code, {"type": "players", "players": self.room_players(room_code)[:4]})

    async def handler(self, ws) -> None:
        ws.player_name = None
        current_room = None

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")
                if msg_type == "join":
                    room = str(msg.get("room", self.join_code)).strip()[:64] or self.join_code
                    current_room = room
                    if current_room not in self.rooms:
                        self.rooms[current_room] = set()
                    self.rooms[current_room].add(ws)
                    await ws.send(json.dumps({"type": "players", "players": self.room_players(current_room)[:4]}))
                elif msg_type == "hello":
                    if current_room is None:
                        continue
                    name = self.unique_player_name(current_room, str(msg.get("name", "Player")), ws)
                    ws.player_name = name
                    await ws.send(json.dumps({"type": "hello_ack", "name": name}))
                    await self.broadcast_roster(current_room)
                elif current_room and current_room in self.rooms:
                    await self.broadcast(current_room, msg, exclude=ws)
        except Exception:
            pass
        finally:
            if current_room and current_room in self.rooms:
                self.rooms[current_room].discard(ws)
                if self.rooms[current_room]:
                    await self.broadcast_roster(current_room)
                else:
                    del self.rooms[current_room]

    async def _serve(self) -> None:
        import websockets

        discovery_thread = threading.Thread(target=self._run_discovery, daemon=True)
        discovery_thread.start()
        try:
            async with websockets.serve(self.handler, "0.0.0.0", self.port):
                self.ready.set()
                while not self.stop_requested.is_set():
                    await asyncio.sleep(0.1)
        except OSError as exc:
            self.error = str(exc)
            self.ready.set()

    def _run_discovery(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
            sock.settimeout(0.5)
            while not self.stop_requested.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                text = data.decode("utf-8", errors="ignore")
                if text == f"HOLOORBIT_DISCOVER:{self.join_code}":
                    response = f"HOLOORBIT_HOST:{self.join_code}:{self.port}".encode("utf-8")
                    sock.sendto(response, addr)
        except OSError:
            pass
        finally:
            sock.close()


def discover_host(join_code: str, timeout: float = 1.6) -> str | None:
    if is_browser_runtime():
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
    except OSError:
        return None
    try:
        payload = f"HOLOORBIT_DISCOVER:{join_code}".encode("utf-8")
        sock.sendto(payload, ("255.255.255.255", DISCOVERY_PORT))
        data, addr = sock.recvfrom(1024)
    except OSError:
        return None
    finally:
        sock.close()
    text = data.decode("utf-8", errors="ignore")
    if text.startswith(f"HOLOORBIT_HOST:{join_code}:"):
        port = text.rsplit(":", 1)[-1]
        if port.isdigit():
            return f"{addr[0]}:{port}"
        return addr[0]
    return None


def is_browser_runtime() -> bool:
    try:
        import platform
        return hasattr(platform, "window")
    except Exception:
        return False


class KeplerGame:
    def __init__(self, multiplayer_mode: str = "solo", host: str = "127.0.0.1", port: int = DEFAULT_PORT, player_name: str = "Player") -> None:
        pygame.init()
        pygame.display.set_caption("Kepler Path - Pygame")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22)
        self.small = pygame.font.SysFont("arial", 16)
        self.micro = pygame.font.SysFont("arial", 12, bold=True)
        self.title = pygame.font.SysFont("arial", 28, bold=True)
        self.heading = pygame.font.SysFont("arial", 34, bold=True)
        self.orbit = Orbit()
        self.center = Vec2(380, 284)
        self.zoom = 0.7
        self.rotation = 0.0
        self.t = 0.0
        self.paused = False
        self.menu_active = multiplayer_mode == "menu"
        self.menu_mode = "name" if self.menu_active else "choose"
        self.pending_menu_mode = "choose"
        self.player_name_input = ""
        self.join_ip = ""
        self.menu_input_focused = False
        self.local_ip = self.detect_local_ip()
        self.default_host = host
        self.default_port = port
        self.local_relay: LocalRelayServer | None = None
        self.screen_state = "ship"
        self.mode = "play"
        self.selected: str | None = None
        self.measurements: list[Measurement] = []
        self.notice = "You and your team must work together to find a secret code that unlocks the doors in the ship. Move with WASD and press E at a console."
        self.background = self.load_background()
        self.planet_texture = self.load_planet_texture()
        self.ship_map = self.load_scaled(SHIP_MAP_PATH, (WIDTH, HEIGHT))
        self.prompt_icon = self.load_scaled(PROMPT_PATH, (44, 44))
        self.player_idle = self.load_scaled(PLAYER_IDLE_PATH, (52, 44))
        self.player_walk = self.load_player_walk()

        self.panel_bg = self.load_scaled(PANEL_BG_PATH, (282, HEIGHT - 112))
        self.frame_bg = self.load_scaled(FRAME_BG_PATH, (704, 394))
        self.dialog_bg = self.load_scaled(DIALOG_BG_PATH, (910, 122))
        self.task_bg = self.load_scaled(TASK_BG_PATH, (248, 34))
        self.kepler_panel = self.load_scaled(KEPLER_PANEL_PATH, (248, 170))
        self.player = pygame.Vector2(279, 148)
        self.player_speed = 230.0
        self.player_facing = "left"
        self.interact_target: Terminal | None = None
        self.active_terminal = "Navigation Bay"
        self.transition_timer = 0.0
        self.transition_label = ""
        self.measure_flash = 0.0
        self.lesson_progress = 0
        self.lesson_success = False
        self.lesson_buttons: dict[str, pygame.Rect] = {}
        self.area_captures: list[AreaCapture] = []
        self.law3_index = 1
        self.tutorial_step = 0
        self.tutorial_active = False
        self.multiplayer_timer = 0.0
        self.exit_menu_active = False
        self.position_sync_timer = 0.0
        self.team_code = JOIN_CODE
        if multiplayer_mode == "host" and not is_browser_runtime():
            self.local_relay = LocalRelayServer(self.default_port, self.team_code)
            if self.local_relay.start():
                host = f"127.0.0.1:{self.default_port}"
        self.network = NetworkSession(multiplayer_mode, host, port, player_name)
        self.crew = [
            CrewMember(player_name, "Navigator", ACCENT, (279, 148), joined=True, ready=True),
            CrewMember("Waiting", "Recorder", (244, 114, 182), (906, 336)),
            CrewMember("Waiting", "Pilot", (76, 217, 100), (676, 236)),
            CrewMember("Waiting", "Observer", (252, 196, 25), (104, 336)),
        ]
        self.terminals = [
            Terminal(
                "Crew Lounge",
                pygame.Rect(104, 344, 92, 76),
                "lounge",
                "Gather here with your crew and press E when you are ready.",
                (56, 189, 248),
            ),
            Terminal(
                "Training Sim",
                pygame.Rect(304, 86, 132, 76),
                "tutorial",
                "Practice the core controls with guided prompts.",
                (56, 189, 248),
            ),
            Terminal(
                "Law 1 Lab",
                pygame.Rect(488, 96, 124, 76),
                "law1",
                "Explore why planets follow ellipses with the star at one focus.",
                (168, 85, 247),
            ),
            Terminal(
                "Law 2 Lab",
                pygame.Rect(462, 328, 132, 102),
                "law2",
                "Capture equal-time orbital sweeps and compare areas.",
                (244, 114, 182),
            ),
            Terminal(
                "Law 3 Lab",
                pygame.Rect(668, 334, 132, 78),
                "law3",
                "Compare period and orbit-size ratios across planets.",
                (252, 196, 25),
            ),
            Terminal(
                "Measure Bay",
                pygame.Rect(292, 334, 132, 78),
                "measure",
                "Measure distances between the star, planet, foci, and apsides.",
                (244, 114, 182),
            ),
            Terminal(
                "Navigation Bay",
                pygame.Rect(678, 150, 130, 78),
                "ship",
                "Return to the crew navigation map.",
                (76, 217, 100),
            ),
        ]
        self.running = True

    def detect_local_ip(self) -> str:
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect(("8.8.8.8", 80))
            ip = probe.getsockname()[0]
            probe.close()
            return ip
        except OSError:
            return "127.0.0.1"

    def start_host_game(self) -> None:
        self.network.close()
        if self.local_relay is not None:
            self.local_relay.stop()
            self.local_relay = None
        name = self.player_name_input.strip() or self.crew[0].name
        name = "Host" if name == "Player" else name
        self.crew[0].name = name
        host = self.default_host
        if not is_browser_runtime():
            self.local_relay = LocalRelayServer(self.default_port, self.team_code)
            if self.local_relay.start():
                host = f"127.0.0.1:{self.default_port}"
            else:
                host = f"127.0.0.1:{self.default_port}"
                self.notice = f"Could not start local relay: {self.local_relay.error}"
        self.network = NetworkSession("host", host, self.default_port, name)
        self.menu_active = False
        self.reset_presentation()
        if self.local_relay and self.local_relay.error:
            self.notice = f"Hosting client started, but local relay failed: {self.local_relay.error}"
        elif is_browser_runtime():
            self.notice = f"Hosting team {self.team_code} on the web relay."
        else:
            self.notice = f"Hosting team {self.team_code}. Other players can enter {JOIN_CODE} or IP {self.local_ip}."

    def start_join_game(self) -> None:
        code_or_host = self.join_ip.strip()
        if not code_or_host:
            return
        if self.local_relay is not None:
            self.local_relay.stop()
            self.local_relay = None
        if code_or_host.upper() == JOIN_CODE:
            fallback_host = self.default_host if is_browser_runtime() else f"127.0.0.1:{self.default_port}"
            host = discover_host(JOIN_CODE) or fallback_host
        else:
            host = code_or_host
            if ":" not in host:
                host = f"{host}:{self.default_port}"
        self.network.close()
        name = self.player_name_input.strip() or self.crew[0].name
        name = "Visitor" if name == "Player" else name
        self.crew[0].name = name
        self.network = NetworkSession("join", host, self.default_port, name)
        self.menu_active = False
        self.reset_presentation()
        self.notice = f"Joining team {self.team_code}."

    def terminal_named(self, name: str) -> Terminal:
        for terminal in self.terminals:
            if terminal.name == name:
                return terminal
        raise ValueError(f"unknown terminal: {name}")

    def sync_crew_names(self, names: list[str]) -> None:
        roles = ["Navigator", "Recorder", "Pilot", "Observer"]
        colors = [ACCENT, (244, 114, 182), (76, 217, 100), (252, 196, 25)]
        for i, member in enumerate(self.crew):
            if i < len(names):
                was_ready = member.ready
                member.name = names[i]
                member.role = roles[i]
                member.color = colors[i]
                member.joined = True
                member.ready = was_ready
            else:
                member.name = "Waiting"
                member.role = roles[i]
                member.color = colors[i]
                member.joined = False
                member.ready = False

    def ensure_remote_crew_member(self, name: str) -> CrewMember | None:
        if not name:
            return None
        existing = self.crew_member_by_name(name)
        if existing is not None:
            return existing

        for member in self.crew:
            if not member.joined:
                member.name = name
                member.joined = True
                member.ready = False
                return member
        return None

    def crew_member_by_name(self, name: str) -> CrewMember | None:
        for member in self.crew:
            if member.name == name:
                return member
        return None

    def local_crew_member(self) -> CrewMember:
        member = self.crew_member_by_name(self.network.name)
        return member if member is not None else self.crew[0]

    def joined_crew(self) -> list[CrewMember]:
        return [member for member in self.crew if member.joined]

    def all_joined_ready(self) -> bool:
        joined = self.joined_crew()
        return bool(joined) and all(member.ready for member in joined)

    def apply_network_messages(self) -> None:
        for message in self.network.poll():
            message_type = message.get("type")
            if message_type == "hello_ack":
                self.crew[0].name = str(message.get("name", self.crew[0].name))
                continue
            if message_type == "players":
                players = [str(name) for name in message.get("players", [])]
                self.sync_crew_names(players[:4])
            elif message_type == "open_terminal":
                name = str(message.get("terminal", "Mars Measure"))
                try:
                    self.open_terminal(self.terminal_named(name), broadcast=False)
                except ValueError:
                    pass
            elif message_type == "measurement":
                start = str(message.get("start", "Red Dwarf"))
                end = str(message.get("end", "Perihelion"))
                t = float(message.get("t", self.t))
                distance = float(message.get("distance", self.distance_between(start, end, t)))
                if not any(m.start == start and m.end == end and abs(m.t - t) < 0.0001 for m in self.measurements):
                    self.measurements.append(Measurement(start, end, distance, t))
                    self.measure_flash = 1.2
                    self.notice = f"Team recorded {start} to {end}: {distance:.1f} units."
            elif message_type == "return_ship":
                self.screen_state = "ship"
                self.active_terminal = "Navigation Bay"
                self.selected = None
                self.notice = "Team returned to the Navigation Bay."
            elif message_type == "player_pos":
                name = str(message.get("name", ""))
                if name == self.network.name:
                    continue
                member = self.ensure_remote_crew_member(name)
                if member is not None:
                    member.pos = (int(message.get("x", member.pos[0])), int(message.get("y", member.pos[1])))
                    member.joined = True
            elif message_type == "ready":
                member = self.crew_member_by_name(str(message.get("name", "")))
                if member is not None:
                    member.ready = bool(message.get("ready", True))

    def load_background(self) -> pygame.Surface | None:
        if not MILKY_WAY_TEXTURE.exists():
            return None
        image = pygame.image.load(str(MILKY_WAY_TEXTURE)).convert()
        return pygame.transform.smoothscale(image, (WIDTH, HEIGHT))

    def load_planet_texture(self) -> pygame.Surface | None:
        if not EARTH_TEXTURE.exists():
            return None
        image = pygame.image.load(str(EARTH_TEXTURE)).convert_alpha()
        return pygame.transform.smoothscale(image, (34, 34))

    def load_scaled(self, path: Path, size: tuple[int, int]) -> pygame.Surface | None:
        if not path.exists():
            return None
        image = pygame.image.load(str(path)).convert_alpha()
        return pygame.transform.smoothscale(image, size)

    def load_player_walk(self) -> list[pygame.Surface]:
        frames = []
        for i in range(1, 15):
            path = PLAYER_SIDE_PATH / f"{i:02}.png"
            frame = self.load_scaled(path, (52, 44))
            if frame is not None:
                frames.append(frame)
        return frames

    def draw_glow_rect(
        self,
        rect: pygame.Rect,
        fill: tuple[int, int, int],
        border: tuple[int, int, int] = PANEL_LIGHT,
        radius: int = 14,
        alpha: int = 235,
        width: int = 2,
    ) -> None:
        shadow = pygame.Surface((rect.width + 18, rect.height + 18), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (*border, 46), shadow.get_rect(), border_radius=radius + 9)
        self.screen.blit(shadow, (rect.x - 9, rect.y - 9))
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (*fill, alpha), surface.get_rect(), border_radius=radius)
        pygame.draw.rect(surface, border, surface.get_rect(), width, border_radius=radius)
        self.screen.blit(surface, rect)

    def draw_wrapped(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        rect: pygame.Rect,
        line_gap: int = 4,
    ) -> None:
        words = text.split()
        x, y = rect.topleft
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= rect.width or not line:
                line = test
                continue
            self.screen.blit(font.render(line, True, color), (x, y))
            y += font.get_linesize() + line_gap
            line = word
            if y > rect.bottom - font.get_linesize():
                return
        if line and y <= rect.bottom - font.get_linesize():
            self.screen.blit(font.render(line, True, color), (x, y))

    def draw_objective(self, text: str) -> None:
        rect = pygame.Rect(18, 18, 318, 48)
        self.draw_glow_rect(rect, PANEL, ACCENT, radius=10, alpha=238, width=1)
        prefix = self.micro.render("OBJECTIVE:", True, ACCENT)
        self.screen.blit(prefix, (30, 27))
        self.draw_wrapped(text, self.micro, ACCENT, pygame.Rect(106, 25, 216, 34), line_gap=0)

    def draw_nav_badge(self) -> None:
        center = (978, 38)
        pygame.draw.circle(self.screen, ACCENT, center, 28, 2)
        pygame.draw.circle(self.screen, (5, 32, 42), center, 22)
        pygame.draw.line(self.screen, ACCENT, (center[0] - 16, center[1]), (center[0] + 16, center[1]), 2)
        pygame.draw.line(self.screen, ACCENT, (center[0], center[1] - 16), (center[0], center[1] + 16), 2)
        pygame.draw.polygon(
            self.screen,
            ACCENT,
            [(center[0], center[1] - 14), (center[0] + 8, center[1] + 4), (center[0], center[1]), (center[0] - 8, center[1] + 4)],
        )

    def draw_dialog(self, speaker: str, message: str, compact: bool = False) -> None:
        if compact:
            outer = pygame.Rect(42, HEIGHT - 104, WIDTH - 84, 78)
        else:
            outer = pygame.Rect(48, HEIGHT - 126, WIDTH - 96, 102)
        pygame.draw.rect(self.screen, TEXT, outer, border_radius=28)
        inner = outer.inflate(-20 if compact else -24, -14 if compact else -20)
        self.draw_glow_rect(inner, PANEL, PANEL_LIGHT, radius=24, alpha=250, width=1)
        if speaker:
            tag = self.small.render(speaker.upper(), True, ACCENT)
            self.screen.blit(tag, (inner.x + 24, inner.y + (8 if compact else 12)))
            text_rect = pygame.Rect(
                inner.x + 24,
                inner.y + (32 if compact else 38),
                inner.width - (116 if compact else 142),
                inner.height - (38 if compact else 46),
            )
        else:
            text_rect = pygame.Rect(inner.x + 24, inner.y + 24, inner.width - 142, inner.height - 40)
        self.draw_wrapped(message, self.small if compact else self.font, TEXT, text_rect, line_gap=1 if compact else 2)
        arrow_x = inner.right - (56 if compact else 78)
        arrow_y = inner.centery
        arrow_h = 30 if compact else 34
        arrow_w = 22 if compact else 26
        pygame.draw.polygon(
            self.screen,
            (221, 255, 255),
            [(arrow_x - 18, arrow_y - arrow_h), (arrow_x + arrow_w, arrow_y), (arrow_x - 18, arrow_y + arrow_h), (arrow_x - 5, arrow_y)],
        )
        pygame.draw.polygon(
            self.screen,
            (98, 242, 248),
            [(arrow_x - 14, arrow_y - arrow_h + 8), (arrow_x + arrow_w - 8, arrow_y), (arrow_x - 14, arrow_y + arrow_h - 8), (arrow_x - 5, arrow_y)],
            2,
        )

    def draw_transition_modal(self) -> None:
        if self.transition_timer <= 0:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((238, 242, 244, 178))
        self.screen.blit(overlay, (0, 0))
        rect = pygame.Rect(160, 110, 704, 360)
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (*MODAL, 224), surface.get_rect(), border_radius=14)
        self.screen.blit(surface, rect)
        close = self.title.render("x", True, MODAL_TEXT)
        self.screen.blit(close, (rect.right - 42, rect.y + 18))
        message = self.transition_label or "Waiting for other players to join the meeting!"
        lines = pygame.Rect(rect.x + 92, rect.y + 142, rect.width - 184, 110)
        self.draw_wrapped(message, self.heading, MODAL_TEXT, lines, line_gap=2)
        joined = sum(member.joined for member in self.crew)
        ready = sum(member.ready for member in self.crew)
        status = self.small.render(f"Team {self.team_code}  |  {joined}/{len(self.crew)} joined  |  {ready}/{len(self.crew)} ready", True, MODAL_TEXT)
        self.screen.blit(status, status.get_rect(center=(rect.centerx, rect.y + 262)))
        pygame.draw.circle(self.screen, STAR, (rect.right - 68, rect.bottom - 50), 20)

    def draw_crew_status(self, rect: pygame.Rect) -> None:
        self.draw_glow_rect(rect, PANEL, PANEL_LIGHT, radius=12, alpha=236, width=1)
        header = f"TEAM {self.team_code}"
        if self.network.mode == "host":
            header = f"HOSTING {self.team_code}"
        elif self.network.mode == "join":
            header = f"JOINED {self.team_code}"
        self.screen.blit(self.micro.render(header, True, ACCENT), (rect.x + 14, rect.y + 12))
        y = rect.y + 36
        for member in self.crew:
            pygame.draw.circle(self.screen, member.color if member.joined else MUTED, (rect.x + 20, y + 8), 5)
            name = member.name.upper()
            if len(name) > 12:
                name = f"{name[:11]}..."
            self.screen.blit(self.micro.render(name, True, TEXT if member.joined else MUTED), (rect.x + 34, y + 1))
            state = "READY" if member.ready else ("JOINED" if member.joined else "WAITING")
            state_color = ACCENT if member.ready else MUTED
            state_text = self.micro.render(state, True, state_color)
            self.screen.blit(state_text, (rect.right - state_text.get_width() - 12, y + 1))
            y += 20

    def draw_start_menu(self) -> None:
        self.screen.fill((194, 199, 204))
        if self.ship_map:
            self.screen.blit(self.ship_map, (0, 0))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((4, 16, 22, 142))
            self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(236, 94, 552, 390)
        self.draw_glow_rect(panel, PANEL, PANEL_LIGHT, radius=18, alpha=248, width=2)
        title = self.heading.render("HOLOORBITS", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 58)))
        subtitle = self.small.render(f"Team Code: {self.team_code}", True, ACCENT)
        self.screen.blit(subtitle, subtitle.get_rect(center=(panel.centerx, panel.y + 96)))

        if self.menu_mode == "name":
            input_rect = pygame.Rect(panel.x + 82, panel.y + 166, panel.width - 164, 54)
            self.draw_glow_rect(input_rect, (16, 64, 76), ACCENT if self.menu_input_focused else MUTED, radius=10, alpha=245, width=1)
            value = self.player_name_input if self.player_name_input else "Type your name"
            color = TEXT if self.player_name_input else MUTED
            name_text = self.title.render(value, True, color)
            self.screen.blit(name_text, name_text.get_rect(center=input_rect.center))
            if self.menu_input_focused and pygame.time.get_ticks() % 1000 < 520:
                name_width = self.title.size(self.player_name_input)[0] if self.player_name_input else 0
                cursor_x = input_rect.centerx + (name_width // 2 + 4 if self.player_name_input else 0)
                pygame.draw.line(self.screen, TEXT, (cursor_x, input_rect.y + 13), (cursor_x, input_rect.bottom - 13), 2)
            continue_rect = pygame.Rect(panel.x + 82, panel.y + 248, panel.width - 164, 62)
            self.draw_glow_rect(continue_rect, BUTTON, PANEL_LIGHT, radius=14, alpha=245, width=2)
            continue_text = self.title.render("CONTINUE", True, TEXT)
            self.screen.blit(continue_text, continue_text.get_rect(center=continue_rect.center))
            hint = self.micro.render("Press Enter or click Continue.", True, MUTED)
            self.screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.y + 338)))
            footer = self.micro.render("Press Esc to quit.", True, MUTED)
            self.screen.blit(footer, footer.get_rect(center=(panel.centerx, panel.bottom - 28)))
            return

        host_rect = pygame.Rect(panel.x + 82, panel.y + 142, panel.width - 164, 62)
        join_rect = pygame.Rect(panel.x + 82, panel.y + 224, panel.width - 164, 62)
        self.draw_glow_rect(host_rect, BUTTON, PANEL_LIGHT, radius=14, alpha=245, width=2)
        self.draw_glow_rect(join_rect, PANEL if self.menu_mode == "join" else BUTTON, PANEL_LIGHT, radius=14, alpha=245, width=2)
        host_text = self.title.render("HOST GAME", True, TEXT)
        join_text = self.title.render("JOIN GAME", True, TEXT)
        self.screen.blit(host_text, host_text.get_rect(center=host_rect.center))
        self.screen.blit(join_text, join_text.get_rect(center=join_rect.center))

        if self.menu_mode == "join":
            input_rect = pygame.Rect(panel.x + 82, panel.y + 306, panel.width - 164, 42)
            self.draw_glow_rect(input_rect, (16, 64, 76), ACCENT if self.menu_input_focused else MUTED, radius=10, alpha=245, width=1)
            value = self.join_ip if self.join_ip else f"Type {JOIN_CODE}, then Enter"
            color = TEXT if self.join_ip else MUTED
            text_surface = self.small.render(value, True, color)
            self.screen.blit(text_surface, (input_rect.x + 16, input_rect.y + 12))
            if self.menu_input_focused and pygame.time.get_ticks() % 1000 < 520:
                cursor_x = input_rect.x + 18 + (self.small.size(self.join_ip)[0] if self.join_ip else 0)
                pygame.draw.line(self.screen, TEXT, (cursor_x, input_rect.y + 10), (cursor_x, input_rect.bottom - 10), 2)
        else:
            hint = self.small.render(f"Host IP: {self.local_ip}", True, MUTED)
            self.screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.y + 328)))

        footer = self.micro.render("Click a button. Press Esc to quit.", True, MUTED)
        self.screen.blit(footer, footer.get_rect(center=(panel.centerx, panel.bottom - 28)))

    def draw_remote_crew(self) -> None:
        for member in self.crew:
            if not member.joined:
                continue
            if member.name == self.network.name:
                continue
            px, py = member.pos
            pygame.draw.ellipse(self.screen, (0, 0, 0, 82), (px - 16, py + 11, 32, 9))
            pygame.draw.rect(self.screen, member.color, (px - 10, py - 20, 20, 28), border_radius=5)
            pygame.draw.circle(self.screen, (245, 249, 252), (px, py - 28), 10)
            visor = pygame.Rect(px - 8, py - 32, 16, 8)
            pygame.draw.rect(self.screen, PANEL, visor, border_radius=4)
            pygame.draw.circle(self.screen, ACCENT, (px - 4, py - 28), 2)
            pygame.draw.circle(self.screen, ACCENT, (px + 4, py - 28), 2)
            self.draw_nameplate(member.name, member.color, px, py)

    def draw_nameplate(self, name: str, color: tuple[int, int, int], px: int, py: int) -> None:
        label = self.micro.render(name.upper(), True, TEXT)
        label_rect = label.get_rect(center=(px, py + 28)).inflate(12, 6)
        pygame.draw.rect(self.screen, PANEL, label_rect, border_radius=5)
        pygame.draw.rect(self.screen, color, label_rect, 1, border_radius=5)
        self.screen.blit(label, label.get_rect(center=label_rect.center))

    def world_to_screen(self, point: Vec2) -> tuple[int, int]:
        rotated = point.rotate(self.rotation)
        scaled = rotated * self.zoom
        return round(self.center.x + scaled.x), round(self.center.y - scaled.y)

    def screen_to_world(self, pos: tuple[int, int]) -> Vec2:
        x = (pos[0] - self.center.x) / self.zoom
        y = -(pos[1] - self.center.y) / self.zoom
        return Vec2(x, y).rotate(-self.rotation)

    def bodies(self) -> dict[str, Body]:
        planet = self.orbit.point_at(self.t)
        return {
            "Red Dwarf": Body("Red Dwarf", Vec2(0, 0), 24, STAR),
            "Perihelion": Body("Perihelion", Vec2(self.orbit.periapsis, 0), 10, PERI),
            "Aphelion": Body("Aphelion", Vec2(-self.orbit.apoapsis, 0), 10, APO),
            "Focus": Body("Focus", Vec2(self.orbit.periapsis - self.orbit.apoapsis, 0), 9, FOCUS),
            "Exoplanet": Body("Exoplanet", planet, 17, PLANET),
        }

    def body_at(self, mouse_pos: tuple[int, int]) -> str | None:
        for body in sorted(self.bodies().values(), key=lambda b: b.radius, reverse=True):
            sx, sy = self.world_to_screen(body.pos)
            if math.hypot(mouse_pos[0] - sx, mouse_pos[1] - sy) <= body.radius + 8:
                return body.name
        return None

    def body_position_at_measurement(self, name: str, t: float) -> Vec2:
        if name == "Exoplanet":
            return self.orbit.point_at(t)
        return self.bodies()[name].pos

    def distance_between(self, start: str, end: str, t: float) -> float:
        start_pos = self.body_position_at_measurement(start, t)
        end_pos = self.body_position_at_measurement(end, t)
        return (start_pos - end_pos).length()

    def start_lesson_mode(self, mode: str) -> None:
        self.mode = mode
        self.selected = None
        self.lesson_progress = 0
        self.lesson_success = False
        self.area_captures.clear()
        self.lesson_buttons.clear()
        self.tutorial_active = mode == "tutorial"
        self.tutorial_step = 0
        if mode == "law1":
            self.paused = True
            self.t = 0.08
        elif mode == "law2":
            self.paused = False
            self.t = 0.94
        elif mode == "law3":
            self.paused = True
            self.law3_index = 1
        elif mode == "tutorial":
            self.paused = False
            self.t = 0.25

    def current_lesson(self) -> LessonMode | None:
        return LESSON_MODES.get(self.mode)

    def adjust_orbit_shape(self, delta: float) -> None:
        new_apoapsis = max(self.orbit.periapsis + 40, min(520, self.orbit.apoapsis + delta))
        self.orbit = Orbit(apoapsis=new_apoapsis, periapsis=self.orbit.periapsis, argument_of_periapsis=self.orbit.argument_of_periapsis)
        eccentricity = self.orbit.eccentricity
        if eccentricity >= 0.48:
            self.lesson_success = True
            self.notice = f"First Law complete: eccentricity {eccentricity:.2f}. The star is clearly at one focus."
        else:
            self.notice = f"Eccentricity is {eccentricity:.2f}. Increase stretch until the empty focus separates from the star."

    def capture_equal_time_area(self) -> None:
        start_t = self.t
        end_t = (self.t + 0.08) % 1.0
        delta_t = (end_t - start_t) % 1.0
        area = math.pi * self.orbit.semi_major_axis * self.orbit.semi_minor_axis * delta_t
        label = "Near perihelion" if start_t > 0.86 or start_t < 0.14 else "Farther from star"
        self.area_captures.append(AreaCapture(start_t, end_t, area, label))
        if len(self.area_captures) > 2:
            self.area_captures.pop(0)
        if len(self.area_captures) == 2:
            a, b = self.area_captures
            difference = abs(a.area - b.area) / max(a.area, b.area)
            self.lesson_success = difference < 0.12
            verdict = "Second Law complete" if self.lesson_success else "Try captures farther apart on the orbit"
            self.notice = f"{verdict}: equal-time area difference is {difference * 100:.1f}%."
        else:
            self.notice = "Captured one equal-time sweep. Let the planet move, then capture another."

    def select_law3_preset(self, delta: int) -> None:
        self.law3_index = (self.law3_index + delta) % len(ORBIT_PRESETS)
        preset = ORBIT_PRESETS[self.law3_index]
        self.lesson_success = self.law3_index == 2
        if self.lesson_success:
            self.notice = "Third Law complete: Mars still has T^2 / a^3 near 1.00."
        else:
            self.notice = f"Selected {preset.name}. Compare the ratio and find another world with the same constant."

    def _handle_tutorial_click(self, clicked: str) -> None:
        if not self.tutorial_active or self.tutorial_step >= len(TUTORIAL_STEPS):
            return
        step = TUTORIAL_STEPS[self.tutorial_step]
        if step.event == "star" and clicked == "Red Dwarf":
            self.selected = clicked
            self.advance_tutorial("star")
        elif step.event == "aphelion_measure" and self.selected == "Red Dwarf" and clicked == "Aphelion":
            measurement_t = self.t
            distance = self.distance_between("Red Dwarf", "Aphelion", measurement_t)
            self.measurements.append(Measurement("Red Dwarf", "Aphelion", distance, measurement_t))
            self.measure_flash = 1.2
            self.advance_tutorial("aphelion_measure")
        elif step.event == "perihelion_measure" and self.selected == "Red Dwarf" and clicked == "Perihelion":
            measurement_t = self.t
            distance = self.distance_between("Red Dwarf", "Perihelion", measurement_t)
            self.measurements.append(Measurement("Red Dwarf", "Perihelion", distance, measurement_t))
            self.measure_flash = 1.2
            self.advance_tutorial("perihelion_measure")
        elif step.event == "continue":
            self.advance_tutorial("continue")
        elif step.target is not None and clicked != step.target:
            self.notice = f"Try clicking {step.target} instead."

    def tutorial_message(self) -> str:
        if self.tutorial_step >= len(TUTORIAL_STEPS):
            return "Tutorial complete. Try the three law labs from the ship."
        return TUTORIAL_STEPS[self.tutorial_step].message

    def advance_tutorial(self, event_name: str) -> None:
        if not self.tutorial_active or self.tutorial_step >= len(TUTORIAL_STEPS):
            return
        if TUTORIAL_STEPS[self.tutorial_step].event != event_name:
            return
        self.tutorial_step += 1
        if self.tutorial_step == 2:
            self.selected = "Red Dwarf"
        self.lesson_success = self.tutorial_step >= len(TUTORIAL_STEPS)
        self.notice = self.tutorial_message()

    def open_terminal(self, terminal: Terminal, broadcast: bool = True) -> None:
        if terminal.activity == "ship":
            self.screen_state = "ship"
            self.active_terminal = "Navigation Bay"
            self.selected = None
            self.notice = "Interact with a door to find your fragment of the code."
            return
        if terminal.activity == "lounge":
            local_member = self.local_crew_member()
            local_member.joined = True
            local_member.ready = not local_member.ready
            if self.network.mode == "solo":
                for member in self.crew:
                    member.joined = True
                    member.ready = True
                local_member.ready = True
            else:
                self.network.send({"type": "ready", "name": self.network.name, "ready": local_member.ready})
            ready = sum(member.ready for member in self.joined_crew())
            total = len(self.joined_crew())
            status = "ready" if local_member.ready else "not ready"
            self.notice = f"Crew Lounge: {ready}/{total} crew ready. You are {status}."
            return
        if self.network.mode != "solo" and not self.all_joined_ready():
            ready = sum(member.ready for member in self.joined_crew())
            total = len(self.joined_crew())
            self.notice = f"Gather at the Crew Lounge first. {ready}/{total} crew ready."
            return
        if terminal.activity != "ship" and self.network.mode == "solo":
            for member in self.crew:
                if member.joined:
                    member.ready = True
        self.interact_target = terminal
        self.active_terminal = terminal.name
        self.mode = terminal.activity
        if terminal.activity in LESSON_MODES:
            self.start_lesson_mode(terminal.activity)
        self.screen_state = "orbit"
        self.selected = None
        self.transition_timer = 0.75
        self.multiplayer_timer = 0.0
        for i, member in enumerate(self.crew):
            if self.network.mode == "solo":
                member.joined = True
                member.ready = True
            else:
                member.ready = False
        self.transition_label = "Waiting for other players to join the meeting!"
        self.notice = f"{terminal.name}: {terminal.description}"
        if broadcast:
            self.network.send({"type": "open_terminal", "terminal": terminal.name})

    def run_demo_step(self) -> None:
        if self.screen_state == "ship":
            terminal = self.terminal_named("Measure Bay")
            self.player.update(terminal.rect.centerx, terminal.rect.centery + 50)
            self.open_terminal(terminal)
            return

        self.mode = "measure"
        self.selected = None
        if not self.measurements:
            measurement_t = self.t
            distance = self.distance_between("Red Dwarf", "Perihelion", measurement_t)
            self.measurements.append(Measurement("Red Dwarf", "Perihelion", distance, measurement_t))
            self.measure_flash = 1.2
            for member in self.crew:
                member.joined = True
                member.ready = True
            self.network.send({
                "type": "measurement",
                "start": "Red Dwarf",
                "end": "Perihelion",
                "distance": distance,
                "t": measurement_t,
            })
            self.notice = f"Recorded Red Dwarf to Perihelion: {distance:.1f} units."
            return

        self.screen_state = "ship"
        self.active_terminal = "Navigation Bay"
        self.selected = None
        self.transition_timer = 0.55
        self.transition_label = "Returning to the Navigation Bay."
        self.network.send({"type": "return_ship"})
        self.notice = "Fragment recorded. Return to the Navigation Bay and choose the next console."

    def reset_presentation(self) -> None:
        self.screen_state = "ship"
        self.mode = "play"
        self.active_terminal = "Navigation Bay"
        self.selected = None
        self.measurements.clear()
        self.t = 0.0
        self.paused = False
        self.transition_timer = 0.0
        self.measure_flash = 0.0
        self.multiplayer_timer = 0.0
        self.lesson_progress = 0
        self.lesson_success = False
        self.lesson_buttons.clear()
        self.area_captures.clear()
        self.tutorial_step = 0
        self.tutorial_active = False
        self.player.update(279, 148)
        self.interact_target = None
        for i, member in enumerate(self.crew):
            if self.network.mode == "solo":
                member.joined = i == 0
                member.ready = i == 0
            else:
                member.ready = member.joined
        self.notice = "You and your team must work together to find a secret code that unlocks the doors in the ship. Move with WASD and press E at a console."

    def handle_key(self, event: pygame.event.Event) -> None:
        if self.menu_active:
            if event.key == pygame.K_ESCAPE and self.menu_mode == "join":
                self.menu_mode = "choose"
                self.menu_input_focused = False
            elif event.key == pygame.K_ESCAPE:
                self.running = False
            else:
                self.handle_menu_key(event)
            return
        if event.key == pygame.K_F5 or (event.key == pygame.K_d and event.mod & pygame.KMOD_SHIFT):
            self.run_demo_step()
        elif event.key == pygame.K_0 or event.key == pygame.K_HOME:
            self.reset_presentation()
        elif self.screen_state == "ship":
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_t:
                self.open_terminal(self.terminal_named("Training Sim"))
            elif event.key == pygame.K_1:
                self.open_terminal(self.terminal_named("Law 1 Lab"))
            elif event.key == pygame.K_2:
                self.open_terminal(self.terminal_named("Law 2 Lab"))
            elif event.key == pygame.K_3:
                self.open_terminal(self.terminal_named("Law 3 Lab"))
            else:
                self.handle_ship_key(event)
        elif event.key == pygame.K_TAB or event.key == pygame.K_q:
            self.exit_menu_active = True
            self.notice = "Review team readiness, then return to the ship."
        elif event.key == pygame.K_e:
            member = self.local_crew_member()
            member.ready = not member.ready
            self.network.send({"type": "ready", "name": self.network.name, "ready": member.ready})
            status = "READY" if member.ready else "WAITING"
            self.notice = f"You are {status} to return to ship. Click the nav icon to toggle the status panel."
        elif event.key == pygame.K_SPACE:
            self.paused = not self.paused
            self.advance_tutorial("pause")
        elif event.key == pygame.K_m:
            self.mode = "measure"
            self.selected = None
            self.notice = "Measure mode: click two bodies to record distance."
        elif event.key == pygame.K_o:
            self.mode = "observe"
            self.selected = None
            self.notice = "Observe mode: inspect labels and prior measurements."
        elif event.key == pygame.K_p:
            self.mode = "play"
            self.selected = None
            self.notice = "Play mode: orbit animation is active."
        elif event.key == pygame.K_r:
            self.t = 0.0
            self.measurements.clear()
            self.selected = None
            self.notice = "Reset orbit and measurements."
        elif event.key == pygame.K_s:
            self.save_measurements()
        elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
            self.zoom = min(1.7, self.zoom + 0.08)
            self.advance_tutorial("zoom")
        elif event.key == pygame.K_MINUS:
            self.zoom = max(0.55, self.zoom - 0.08)
            self.advance_tutorial("zoom")
        elif event.key == pygame.K_LEFT:
            self.rotation -= 0.08
        elif event.key == pygame.K_RIGHT:
            self.rotation += 0.08
        elif event.key == pygame.K_BACKSPACE and self.measurements:
            self.measurements.pop()
            self.notice = "Deleted latest measurement."
        elif self.mode == "law1" and event.key == pygame.K_RIGHTBRACKET:
            self.adjust_orbit_shape(35)
        elif self.mode == "law1" and event.key == pygame.K_LEFTBRACKET:
            self.adjust_orbit_shape(-35)
        elif self.mode == "law2" and event.key == pygame.K_c:
            self.capture_equal_time_area()
        elif self.mode == "law3" and event.key == pygame.K_RIGHTBRACKET:
            self.select_law3_preset(1)
        elif self.mode == "law3" and event.key == pygame.K_LEFTBRACKET:
            self.select_law3_preset(-1)

    def handle_menu_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.running = False
            return
        if self.menu_mode == "name":
            if event.key == pygame.K_RETURN:
                if self.player_name_input.strip():
                    self.crew[0].name = self.player_name_input.strip()
                    self.menu_mode = "choose"
                    self.menu_input_focused = False
            elif not self.menu_input_focused:
                return
            elif event.key == pygame.K_BACKSPACE:
                self.player_name_input = self.player_name_input[:-1]
            elif event.unicode and (event.unicode.isalnum() or event.unicode in " _-"):
                if len(self.player_name_input) < 12:
                    self.player_name_input += event.unicode
            return
        if self.menu_mode == "choose":
            if event.key == pygame.K_h:
                self.start_host_game()
            elif event.key == pygame.K_j:
                self.menu_mode = "join"
                self.menu_input_focused = True
            return
        if self.menu_mode == "join":
            if event.key == pygame.K_RETURN:
                self.start_join_game()
            elif event.key == pygame.K_ESCAPE:
                self.menu_mode = "choose"
                self.menu_input_focused = False
            elif not self.menu_input_focused:
                return
            elif event.key == pygame.K_BACKSPACE:
                self.join_ip = self.join_ip[:-1]
            elif event.unicode and (event.unicode.isalnum() or event.unicode in ".-"):
                self.join_ip += event.unicode.upper()

    def handle_ship_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_e:
            if self.interact_target is None:
                self.notice = "Move closer to a console, then press E."
                return
            if self.interact_target.activity == "ship":
                self.notice = "Already in the Navigation Bay."
                return
            self.open_terminal(self.interact_target)

    def handle_click(self, pos: tuple[int, int]) -> None:
        if self.menu_active:
            panel = pygame.Rect(236, 94, 552, 390)
            if self.menu_mode == "name":
                input_rect = pygame.Rect(panel.x + 82, panel.y + 166, panel.width - 164, 54)
                continue_rect = pygame.Rect(panel.x + 82, panel.y + 248, panel.width - 164, 62)
                if input_rect.collidepoint(pos):
                    self.menu_input_focused = True
                elif continue_rect.collidepoint(pos) and self.player_name_input.strip():
                    self.crew[0].name = self.player_name_input.strip()
                    self.menu_mode = "choose"
                    self.menu_input_focused = False
                else:
                    self.menu_input_focused = False
                return
            host_rect = pygame.Rect(panel.x + 82, panel.y + 142, panel.width - 164, 62)
            join_rect = pygame.Rect(panel.x + 82, panel.y + 224, panel.width - 164, 62)
            join_input_rect = pygame.Rect(panel.x + 82, panel.y + 306, panel.width - 164, 42)
            if host_rect.collidepoint(pos):
                self.start_host_game()
            elif join_rect.collidepoint(pos):
                if self.menu_mode == "join" and self.join_ip.strip():
                    self.start_join_game()
                else:
                    self.menu_mode = "join"
                    self.menu_input_focused = True
            elif self.menu_mode == "join" and join_input_rect.collidepoint(pos):
                self.menu_input_focused = True
            else:
                self.menu_input_focused = False
            return
        if self.screen_state == "ship":
            for terminal in self.terminals:
                if terminal.rect.collidepoint(pos):
                    self.player.update(terminal.rect.centerx, terminal.rect.centery + 50)
                    self.interact_target = terminal
                    self.notice = f"{terminal.name}: press E to open."
                    return
            return
        
        # Check nav badge click (top right circle)
        nav_center = (978, 38)
        if math.hypot(pos[0] - nav_center[0], pos[1] - nav_center[1]) <= 32:
            self.exit_menu_active = not self.exit_menu_active
            self.advance_tutorial("nav")
            return

        # Check return to ship button in exit menu
        if self.exit_menu_active:
            panel = pygame.Rect(212, 116, 600, 360)
            btn_rect = pygame.Rect(panel.centerx - 110, panel.bottom - 80, 220, 46)
            if btn_rect.collidepoint(pos):
                is_host = self.network.mode == "host" or self.network.mode == "solo"
                if is_host and self.all_joined_ready():
                    self.exit_menu_active = False
                    self.screen_state = "ship"
                    self.selected = None
                    self.active_terminal = "Navigation Bay"
                    self.transition_timer = 0.55
                    self.transition_label = "Returning to the Navigation Bay."
                    self.network.send({"type": "return_ship"})
                    self.notice = "Interact with a door to find your fragment of the code."
                elif is_host:
                    self.notice = "Waiting for all crew to press E."
                else:
                    self.notice = "Only the host can initiate return to ship."
            return

        for action, rect in self.lesson_buttons.items():
            if rect.collidepoint(pos):
                if action == "law1_less":
                    self.adjust_orbit_shape(-35)
                elif action == "law1_more":
                    self.adjust_orbit_shape(35)
                elif action == "law2_capture":
                    self.capture_equal_time_area()
                elif action == "law3_prev":
                    self.select_law3_preset(-1)
                elif action == "law3_next":
                    self.select_law3_preset(1)
                return

        clicked = self.body_at(pos)
        if self.mode != "measure":
            if clicked:
                if self.mode == "tutorial":
                    self._handle_tutorial_click(clicked)
                else:
                    self.notice = f"{clicked}: screen position {pos[0]}, {pos[1]}"
            return

        if clicked is None:
            self.notice = "Click Red Dwarf, Perihelion, Aphelion, Exoplanet, or Focus."
            return
        if self.selected is None:
            self.selected = clicked
            self.notice = f"Selected {clicked}. Choose the second body."
            return
        if clicked == self.selected:
            self.notice = "Choose a different second body."
            return

        measurement_t = self.t
        distance = self.distance_between(self.selected, clicked, measurement_t)
        start = self.selected
        self.measurements.append(Measurement(self.selected, clicked, distance, measurement_t))
        self.measure_flash = 1.2
        self.notice = f"Recorded {self.selected} to {clicked}: {distance:.1f} units."
        self.network.send({
            "type": "measurement",
            "start": start,
            "end": clicked,
            "distance": distance,
            "t": measurement_t,
        })
        self.selected = None

    def save_measurements(self) -> None:
        out_dir = Path(__file__).resolve().parent / "logs"
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / f"measurements_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        with out_file.open("w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["start", "end", "distance", "orbit_t"])
            for m in self.measurements:
                writer.writerow([m.start, m.end, f"{m.distance:.3f}", f"{m.t:.6f}"])
        self.notice = f"Saved {len(self.measurements)} measurements to {out_file.name}."

    def update(self, dt: float) -> None:
        if self.menu_active:
            return
        self.apply_network_messages()
        self.update_multiplayer(dt)
        if self.screen_state == "ship":
            self.update_ship(dt)
            self.sync_local_player_position(dt)
            self.transition_timer = max(0.0, self.transition_timer - dt)
            return
        self.sync_local_player_position(dt)
        if not self.paused:
            self.t = (self.t + dt * 0.035) % 1.0
        self.transition_timer = max(0.0, self.transition_timer - dt)
        self.measure_flash = max(0.0, self.measure_flash - dt)

    def sync_local_player_position(self, dt: float) -> None:
        self.local_crew_member().pos = (round(self.player.x), round(self.player.y))
        if self.network.mode == "solo":
            return
        self.position_sync_timer += dt
        if self.position_sync_timer < 0.08:
            return
        self.position_sync_timer = 0.0
        self.network.send({
            "type": "player_pos",
            "name": self.network.name,
            "x": round(self.player.x),
            "y": round(self.player.y),
        })

    def update_multiplayer(self, dt: float) -> None:
        if self.screen_state != "orbit":
            return
        if self.network.mode != "solo":
            return
        self.multiplayer_timer += dt
        join_times = [0.0, 0.35, 0.7, 1.05]
        ready_times = [0.0, 0.75, 1.1, 1.45]
        for i, member in enumerate(self.crew):
            if self.multiplayer_timer >= join_times[i]:
                member.joined = True
            if self.multiplayer_timer >= ready_times[i]:
                member.ready = True

    def update_ship(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            direction.x -= 1
            self.player_facing = "left"
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            direction.x += 1
            self.player_facing = "right"

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            direction.y -= 1
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            direction.y += 1

        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.player += direction * self.player_speed * dt
            self.player.x = max(46, min(WIDTH - 46, self.player.x))
            self.player.y = max(80, min(HEIGHT - 58, self.player.y))

        self.interact_target = None
        player_rect = pygame.Rect(round(self.player.x - 18), round(self.player.y - 24), 36, 48)
        for terminal in self.terminals:
            interact_area = terminal.rect.inflate(58, 70)
            if interact_area.colliderect(player_rect):
                self.interact_target = terminal
                break

    def draw_text(self, text: str, x: int, y: int, color: tuple[int, int, int] = TEXT) -> None:
        self.screen.blit(self.font.render(text, True, color), (x, y))

    def draw_action_button(self, key: str, rect: pygame.Rect, label: str, active: bool = True) -> None:
        color = ACCENT if active else MUTED
        self.lesson_buttons[key] = rect
        self.draw_glow_rect(rect, (16, 55, 68), color, radius=8, alpha=245, width=1)
        font = self.small
        while font.size(label)[0] > rect.width - 14 and font.get_height() > 12:
            font = pygame.font.SysFont("arial", max(12, font.get_height() - 1))
        text = font.render(label, True, TEXT if active else MUTED)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_tutorial_highlight(self) -> None:
        if not self.tutorial_active or self.tutorial_step >= len(TUTORIAL_STEPS):
            return
        target = TUTORIAL_STEPS[self.tutorial_step].target
        if target is None:
            return
        if target == "nav":
            pos: tuple[int, int] = (978, 38)
            base_radius = 28
        else:
            bodies = self.bodies()
            if target not in bodies:
                return
            pos = self.world_to_screen(bodies[target].pos)
            base_radius = bodies[target].radius
        pulse = int(math.sin(pygame.time.get_ticks() / 300) * 4)
        pygame.draw.circle(self.screen, ACCENT, pos, base_radius + 18 + pulse, 2)
        pygame.draw.circle(self.screen, ACCENT, pos, base_radius + 10, 1)

    def draw_law2_captures(self) -> None:
        for capture in self.area_captures:
            start = self.world_to_screen(self.orbit.point_at(capture.start_t))
            end = self.world_to_screen(self.orbit.point_at(capture.end_t))
            star = self.world_to_screen(Vec2(0, 0))
            sweep = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(sweep, (*MEASURE, 74), [star, start, end])
            self.screen.blit(sweep, (0, 0))
            pygame.draw.line(self.screen, MEASURE, star, start, 2)
            pygame.draw.line(self.screen, MEASURE, star, end, 2)

    def draw_lesson_panel(self, rect: pygame.Rect) -> None:
        self.lesson_buttons.clear()
        lesson = self.current_lesson()
        if lesson is None:
            return
        self.draw_glow_rect(rect, PANEL, PANEL_LIGHT, radius=12, alpha=240, width=1)
        self.screen.blit(self.micro.render(lesson.law.upper(), True, ACCENT), (rect.x + 18, rect.y + 14))
        self.screen.blit(self.title.render(lesson.title, True, TEXT), (rect.x + 18, rect.y + 34))
        self.draw_wrapped(lesson.objective, self.small, TEXT, pygame.Rect(rect.x + 18, rect.y + 72, rect.width - 36, 80), line_gap=1)
        y = rect.y + 158

        if self.mode == "law1":
            e = self.orbit.eccentricity
            self.draw_wrapped(lesson.description, self.micro, MUTED, pygame.Rect(rect.x + 18, y, rect.width - 36, 64), line_gap=0)
            self.screen.blit(self.small.render(f"Eccentricity: {e:.2f}", True, ACCENT), (rect.x + 18, y + 70))
            self.draw_action_button("law1_less", pygame.Rect(rect.x + 18, y + 100, 92, 34), "Less")
            self.draw_action_button("law1_more", pygame.Rect(rect.x + 126, y + 100, 92, 34), "More")
        elif self.mode == "law2":
            self.draw_wrapped(lesson.description, self.micro, MUTED, pygame.Rect(rect.x + 18, y, rect.width - 36, 84), line_gap=0)
            self.draw_action_button("law2_capture", pygame.Rect(rect.x + 18, y + 94, rect.width - 36, 38), "Capture sweep")
            cy = y + 144
            for capture in self.area_captures:
                label_text = self.micro.render(f"{capture.label}:", True, TEXT)
                area_text = self.micro.render(f"{capture.area:.0f}", True, TEXT)
                self.screen.blit(label_text, (rect.x + 18, cy))
                self.screen.blit(area_text, (rect.right - 18 - area_text.get_width(), cy))
                cy += 18
        elif self.mode == "law3":
            preset = ORBIT_PRESETS[self.law3_index]
            ratio = preset.period ** 2 / preset.semi_major_axis ** 3
            self.draw_wrapped(lesson.description, self.micro, MUTED, pygame.Rect(rect.x + 18, y, rect.width - 36, 56), line_gap=0)
            self.screen.blit(self.font.render(preset.name, True, TEXT), (rect.x + 18, y + 64))
            self.screen.blit(self.small.render(f"a = {preset.semi_major_axis:.2f} AU", True, MUTED), (rect.x + 18, y + 96))
            self.screen.blit(self.small.render(f"T = {preset.period:.2f} years", True, MUTED), (rect.x + 18, y + 122))
            self.screen.blit(self.small.render(f"T^2 / a^3 = {ratio:.2f}", True, ACCENT), (rect.x + 18, y + 148))
            self.draw_action_button("law3_prev", pygame.Rect(rect.x + 18, y + 180, 92, 32), "Prev")
            self.draw_action_button("law3_next", pygame.Rect(rect.x + 126, y + 180, 92, 32), "Next")
        elif self.mode == "tutorial":
            self.draw_wrapped(self.tutorial_message(), self.font, TEXT, pygame.Rect(rect.x + 18, y, rect.width - 36, 82), line_gap=2)
            progress = min(self.tutorial_step, len(TUTORIAL_STEPS))
            self.screen.blit(self.small.render(f"Progress: {progress}/{len(TUTORIAL_STEPS)}", True, ACCENT), (rect.x + 18, y + 104))

        if self.lesson_success:
            complete = pygame.Rect(rect.x + 18, rect.bottom - 44, rect.width - 36, 30)
            pygame.draw.rect(self.screen, (28, 96, 76), complete, border_radius=7)
            self.screen.blit(self.micro.render("COMPLETE - return to ship or try another lab", True, TEXT), (complete.x + 10, complete.y + 8))

    def draw_scene(self) -> None:
        if self.menu_active:
            self.draw_start_menu()
            return
        if self.screen_state == "ship":
            self.draw_ship()
            return

        if self.background:
            self.screen.blit(self.background, (0, 0))
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            tint.fill((0, 0, 0, 130))
            self.screen.blit(tint, (0, 0))
        else:
            self.screen.fill(BACKGROUND)

        pygame.draw.rect(self.screen, (5, 24, 35), (32, 84, 700, 408), border_radius=18)
        pygame.draw.rect(self.screen, PANEL_LIGHT, (32, 84, 700, 408), 2, border_radius=18)
        if self.frame_bg:
            self.screen.blit(self.frame_bg, (18, 92))

        points = [self.world_to_screen(p) for p in self.orbit.polyline()]
        pygame.draw.lines(self.screen, ORBIT, False, points, 2)

        for m in self.measurements:
            start = self.world_to_screen(self.body_position_at_measurement(m.start, m.t))
            end = self.world_to_screen(self.body_position_at_measurement(m.end, m.t))
            width = 4 if self.measure_flash > 0 and m == self.measurements[-1] else 2
            pygame.draw.line(self.screen, MEASURE, start, end, width)
            mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
            value = self.small.render(f"{m.distance:.1f} units", True, MEASURE)
            bg_rect = value.get_rect(center=(mid[0], mid[1] - 14)).inflate(14, 8)
            pygame.draw.rect(self.screen, PANEL, bg_rect, border_radius=6)
            pygame.draw.rect(self.screen, MEASURE, bg_rect, 1, border_radius=6)
            self.screen.blit(value, value.get_rect(center=bg_rect.center))
            for name in (m.start, m.end):
                if name == "Exoplanet":
                    ghost = self.world_to_screen(self.orbit.point_at(m.t))
                    pygame.draw.circle(self.screen, (130, 150, 170), ghost, 10, 1)

        if self.mode == "law2":
            self.draw_law2_captures()

        bodies = self.bodies()
        label_offsets = {
            "Red Dwarf": (-44, 34),
            "Perihelion": (16, 36),
            "Aphelion": (18, -8),
            "Focus": (18, -8),
            "Exoplanet": (20, -48),
        }
        pending_labels = []
        for body in bodies.values():
            pos = self.world_to_screen(body.pos)
            if self.mode == "measure":
                pulse = 2 + int((math.sin(pygame.time.get_ticks() / 180) + 1) * 2)
                pygame.draw.circle(self.screen, MEASURE if body.name == self.selected else ACCENT, pos, body.radius + 11 + pulse, 1)
            if body.name == "Exoplanet" and self.planet_texture:
                rect = self.planet_texture.get_rect(center=pos)
                self.screen.blit(self.planet_texture, rect)
            else:
                pygame.draw.circle(self.screen, body.color, pos, body.radius)
                pygame.draw.circle(self.screen, (255, 255, 255), pos, body.radius, 1)
            label = self.small.render(body.name, True, TEXT)
            offset = label_offsets.get(body.name, (body.radius + 6, -8))
            rect = label.get_rect(topleft=(pos[0] + offset[0], pos[1] + offset[1]))
            pending_labels.append((label, rect))

        placed_labels: list[pygame.Rect] = []
        for label, rect in pending_labels:
            rect = rect.copy()
            for placed in placed_labels:
                if rect.colliderect(placed.inflate(8, 4)):
                    rect.y = placed.bottom + 5
            rect.x = max(40, min(704 - rect.width, rect.x))
            rect.y = max(100, min(466 - rect.height, rect.y))
            bg = rect.inflate(8, 4)
            pygame.draw.rect(self.screen, (5, 24, 35), bg, border_radius=4)
            self.screen.blit(label, rect)
            placed_labels.append(rect)

        if self.selected:
            selected = bodies[self.selected]
            pygame.draw.circle(self.screen, MEASURE, self.world_to_screen(selected.pos), selected.radius + 8, 2)

        self.draw_tutorial_highlight()

    def draw_panel(self) -> None:
        if self.menu_active:
            return
        if self.screen_state == "ship":
            self.draw_objective("Interact with a door to find your fragment of the code.")
            self.draw_nav_badge()
            self.draw_crew_status(pygame.Rect(790, 92, 204, 118))
            message = self.notice
            if self.interact_target:
                message = f"{self.interact_target.name}: press E to open this console."
            self.draw_dialog("Nova", message)
            self.draw_transition_modal()
            return

        lesson = self.current_lesson()
        objective = lesson.objective if lesson else "Use the simulation console to compare orbital distances."
        if self.interact_target:
            objective = self.interact_target.description
        self.draw_objective(objective)
        self.draw_nav_badge()

        if lesson:
            self.draw_lesson_panel(pygame.Rect(752, 92, 238, 380))
            if self.measure_flash > 0 and self.measurements:
                latest = self.measurements[-1]
                banner = pygame.Rect(212, 82, 330, 48)
                self.draw_glow_rect(banner, PANEL, MEASURE, radius=10, alpha=246, width=2)
                text = f"Distance captured: {latest.distance:.1f} units"
                self.screen.blit(self.small.render(text, True, TEXT), (banner.x + 22, banner.y + 14))
            if self.exit_menu_active:
                self.draw_exit_status_panel()
            return

        status = pygame.Rect(752, 92, 238, 220)
        self.draw_glow_rect(status, PANEL, PANEL_LIGHT, radius=12, alpha=240, width=1)
        self.screen.blit(self.title.render(self.active_terminal, True, TEXT), (status.x + 20, status.y + 18))
        self.screen.blit(self.font.render(f"Mode: {self.mode.title()}", True, ACCENT), (status.x + 20, status.y + 62))
        self.screen.blit(self.small.render(f"Orbit t: {self.t:.3f}", True, MUTED), (status.x + 20, status.y + 96))
        self.screen.blit(self.small.render("Paused" if self.paused else "Running", True, MUTED), (status.x + 20, status.y + 122))
        ready = sum(member.ready for member in self.crew)
        self.screen.blit(self.font.render(f"Team ready: {ready}/{len(self.crew)}", True, ACCENT), (status.x + 20, status.y + 146))
        controls = "Tab return  Space pause\nM measure  O observe  +/- zoom"
        self.draw_wrapped(controls, self.micro, MUTED, pygame.Rect(status.x + 20, status.y + 178, status.width - 40, 34), line_gap=0)

        log = pygame.Rect(752, 330, 238, 142)
        self.draw_glow_rect(log, PANEL, PANEL_LIGHT, radius=12, alpha=230, width=1)
        self.screen.blit(self.font.render("Mission Log", True, TEXT), (log.x + 20, log.y + 16))
        if not self.measurements:
            self.draw_wrapped("No measurements yet.", self.small, MUTED, pygame.Rect(log.x + 20, log.y + 40, log.width - 40, 44))
        else:
            y = log.y + 48
            row_height = 40
            visible_count = max(1, (log.bottom - y - 12) // row_height)
            visible_measurements = self.measurements[-visible_count:]
            start_index = len(self.measurements) - len(visible_measurements) + 1
            for i, m in enumerate(visible_measurements, start=start_index):
                text = f"{i}. {m.start} -> {m.end}"
                self.screen.blit(self.small.render(text, True, TEXT), (log.x + 20, y))
                self.screen.blit(self.micro.render(f"{m.distance:.1f} units @ {m.t:.2f}", True, MUTED), (log.x + 30, y + 20))
                y += row_height

        if self.measure_flash > 0 and self.measurements:
            latest = self.measurements[-1]
            banner = pygame.Rect(212, 82, 330, 48)
            self.draw_glow_rect(banner, PANEL, MEASURE, radius=10, alpha=246, width=2)
            text = f"Distance captured: {latest.distance:.1f} units"
            self.screen.blit(self.small.render(text, True, TEXT), (banner.x + 22, banner.y + 14))

        if self.exit_menu_active:
            self.draw_exit_status_panel()

    def draw_exit_status_panel(self) -> None:
        panel = pygame.Rect(212, 116, 600, 360)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 16, 22, 180))
        self.screen.blit(overlay, (0, 0))

        self.draw_glow_rect(panel, PANEL, PANEL_LIGHT, radius=20, alpha=252, width=2)
        title = self.title.render("MISSION COMPLETION STATUS", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 44)))

        hint = self.micro.render("Press E to toggle your readiness. Click the Nav icon to return to task.", True, MUTED)
        self.screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.y + 82)))

        joined = self.joined_crew()
        if joined:
            spacing = panel.width // (len(joined) + 1)
            for i, member in enumerate(joined):
                cx = panel.x + spacing * (i + 1)
                cy = panel.y + 180

                # Ready square (Decently sized)
                if member.ready:
                    pygame.draw.rect(self.screen, member.color, (cx - 40, cy - 60, 80, 80), border_radius=12)
                    pygame.draw.rect(self.screen, TEXT, (cx - 40, cy - 60, 80, 80), 2, border_radius=12)
                else:
                    # Slot placeholder
                    pygame.draw.rect(self.screen, (20, 40, 50), (cx - 40, cy - 60, 80, 80), border_radius=12)
                    pygame.draw.rect(self.screen, MUTED, (cx - 40, cy - 60, 80, 80), 1, border_radius=12)

                # Name label at bottom
                name_label = self.small.render(member.name.upper(), True, TEXT)
                self.screen.blit(name_label, name_label.get_rect(center=(cx, cy + 50)))
                role_label = self.micro.render(member.role, True, member.color)
                self.screen.blit(role_label, role_label.get_rect(center=(cx, cy + 72)))

        # Return button (Host Only)
        btn_rect = pygame.Rect(panel.centerx - 110, panel.bottom - 80, 220, 46)
        all_ready = self.all_joined_ready()
        is_host = self.network.mode == "host" or self.network.mode == "solo"

        btn_color = ACCENT if (all_ready and is_host) else MUTED
        self.draw_glow_rect(btn_rect, (20, 45, 55), btn_color, radius=10, alpha=255, width=2)

        btn_label = "RETURN TO SHIP" if is_host else "WAITING FOR HOST"
        label = self.small.render(btn_label, True, btn_color)
        self.screen.blit(label, label.get_rect(center=btn_rect.center))

    def terminal_visual_rect(self, terminal: Terminal) -> pygame.Rect:
        visual_bounds = {
            "Crew Lounge": pygame.Rect(164, 250, 92, 106),
            "Training Sim": pygame.Rect(302, 84, 190, 156),
            "Law 1 Lab": pygame.Rect(508, 176, 168, 108),
            "Law 2 Lab": pygame.Rect(540, 350, 174, 100),
            "Law 3 Lab": pygame.Rect(750, 250, 110, 108),
            "Measure Bay": pygame.Rect(302, 252, 164, 128),
            "Navigation Bay": pygame.Rect(476, 286, 178, 46),
        }
        return visual_bounds.get(terminal.name, terminal.rect)

    def terminal_label_center(self, terminal: Terminal, visual_rect: pygame.Rect) -> tuple[int, int]:
        if terminal.name == "Navigation Bay":
            return visual_rect.center
        if terminal.name == "Law 2 Lab":
            return visual_rect.center
        upper_labels = {"Training Sim", "Law 1 Lab"}
        if terminal.name in upper_labels:
            if self.interact_target == terminal:
                return visual_rect.centerx, visual_rect.y + 62
            return visual_rect.centerx, visual_rect.y + 18
        return visual_rect.centerx, visual_rect.bottom - 18

    def terminal_label_bounds(self, terminal: Terminal, visual_rect: pygame.Rect) -> pygame.Rect:
        if terminal.name == "Law 2 Lab":
            return visual_rect.inflate(-12, -12)
        return visual_rect.inflate(-10, -10)

    def draw_ship(self) -> None:
        self.screen.fill((194, 199, 204))
        if self.ship_map:
            self.screen.blit(self.ship_map, (0, 0))
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            tint.fill((244, 247, 249, 16))
            self.screen.blit(tint, (0, 0))
        else:
            pygame.draw.rect(self.screen, (244, 246, 248), (84, 24, 856, 510), border_radius=8)
            pygame.draw.rect(self.screen, SHIP_WALL, (84, 24, 856, 510), 4, border_radius=8)

        for terminal in self.terminals:
            visual_rect = self.terminal_visual_rect(terminal)
            label = self.micro.render(terminal.name.upper(), True, TEXT)
            label_rect = label.get_rect(center=self.terminal_label_center(terminal, visual_rect))
            badge_rect = label_rect.inflate(14, 8)
            badge_rect.clamp_ip(self.terminal_label_bounds(terminal, visual_rect))
            label_rect.center = badge_rect.center
            pygame.draw.rect(self.screen, PANEL, badge_rect, border_radius=6)
            pygame.draw.rect(self.screen, terminal.color, badge_rect, 2, border_radius=6)
            self.screen.blit(label, label_rect)
            if self.interact_target == terminal and terminal.name != "Navigation Bay":
                pygame.draw.rect(self.screen, terminal.color, visual_rect.inflate(8, 8), 3, border_radius=8)
                prompt_center = (visual_rect.centerx, visual_rect.y + 24)
                if self.prompt_icon:
                    prompt_rect = self.prompt_icon.get_rect(center=prompt_center)
                    self.screen.blit(self.prompt_icon, prompt_rect)
                else:
                    prompt = self.font.render("E", True, BACKGROUND)
                    pygame.draw.circle(self.screen, TEXT, prompt_center, 17)
                    self.screen.blit(prompt, prompt.get_rect(center=prompt_center))

        self.draw_remote_crew()

        px = round(self.player.x)
        py = round(self.player.y)
        pygame.draw.ellipse(self.screen, (0, 0, 0, 90), (px - 18, py + 12, 36, 10))
        sprite = self.player_idle
        keys = pygame.key.get_pressed()
        moving = keys[pygame.K_a] or keys[pygame.K_d] or keys[pygame.K_w] or keys[pygame.K_s]
        if moving and self.player_walk:
            sprite = self.player_walk[(pygame.time.get_ticks() // 70) % len(self.player_walk)]
        if sprite:
            if self.player_facing == "right":
                sprite = pygame.transform.flip(sprite, True, False)
            self.screen.blit(sprite, sprite.get_rect(center=(px, py - 18)))

            member = self.local_crew_member()
            self.draw_nameplate(member.name, member.color, px, py)
        else:
            pygame.draw.rect(self.screen, (82, 190, 255), (px - 13, py - 22, 26, 36), border_radius=5)
            pygame.draw.circle(self.screen, (228, 236, 246), (px, py - 31), 12)

        if self.interact_target and self.interact_target.name != "Navigation Bay":
            self.notice = f"{self.interact_target.name}: press E to open."

    async def run(self) -> None:
        self.network.start()
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

            self.update(dt)
            self.draw_scene()
            self.draw_panel()
            pygame.display.flip()
            await asyncio.sleep(0)
        self.network.close()
        if self.local_relay is not None:
            self.local_relay.stop()
            self.local_relay = None
        pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Kepler Path Pygame prototype")
    parser.add_argument("--host-session", action="store_true", help="Host an optional LAN session")
    parser.add_argument("--join", metavar="HOST", help="Join an optional LAN session")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--name", default="Player")
    args = parser.parse_args()

    mode = "menu"
    host = "127.0.0.1:3000"
    port = 3000
    if args.host_session:
        mode = "host"
    elif args.join:
        mode = "join"
        host = args.join

    if ":" not in host:
        host = f"{host}:{args.port}"
    port = args.port

    async def runner() -> None:
        game = KeplerGame(mode, host, port, args.name)
        await game.run()

    asyncio.run(runner())


def demo_check() -> str:
    game = KeplerGame()
    game.update(1 / 60)
    if game.screen_state != "ship":
        raise RuntimeError("demo must start in the spaceship navigation bay")
    game.draw_scene()
    game.draw_panel()
    pygame.display.flip()

    game.screen_state = "orbit"
    game.mode = "measure"
    game.handle_click(game.world_to_screen(game.bodies()["Red Dwarf"].pos))
    game.handle_click(game.world_to_screen(game.bodies()["Perihelion"].pos))
    if len(game.measurements) != 1:
        raise RuntimeError("measurement smoke test failed")
    distance = game.measurements[0].distance
    pygame.quit()
    return f"demo check ok: recorded distance {distance:.1f} units"


if __name__ == "__main__":
    main()
