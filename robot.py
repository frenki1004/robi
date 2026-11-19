"""Talks to the Ecovacs cloud. Stateless: every call asks the robot directly,
so it works the same on a laptop and in a Vercel serverless function.

Commands and status queries go over Ecovacs' REST API (no MQTT connection),
which is what lets this run without a long-lived process.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import aiohttp

from deebot_client.api_client import ApiClient
from deebot_client.authentication import Authenticator, create_rest_config
from deebot_client.device import Device
from deebot_client.events import (
    BatteryEvent,
    ErrorEvent,
    RoomsEvent,
    StateEvent,
    StatsEvent,
)
from deebot_client.events.station import State as StationState
from deebot_client.events.station import StationEvent
from deebot_client.commands.json.custom import CustomCommand
from deebot_client.commands.json.map import GetMapSubSet
from deebot_client.events.map import MapSetType
from deebot_client.exceptions import AuthenticationError
from deebot_client.models import AccountCredentials, CleanAction, CleanMode, State
from deebot_client.rs.util import decompress_base64_data

# Ecovacs room icon number -> default English room name (same table the app uses)
ROOM_ICON_NAMES = dict(GetMapSubSet._ROOM_NUM_TO_NAME)  # noqa: SLF001

ROOMS_TTL = 15 * 60
log = logging.getLogger(__name__)  # rooms change rarely; refetch every 15 minutes

STATE_NAMES = {
    State.IDLE: "idle",
    State.CLEANING: "cleaning",
    State.RETURNING: "returning",
    State.DOCKED: "docked",
    State.ERROR: "error",
    State.PAUSED: "paused",
}
# getWorkState -> robotState.state values; unknown ones fall back to getCleanInfo
WORK_STATES = {
    "cleaning": "cleaning",
    "clean": "cleaning",
    "washing": "cleaning",  # mid-job mop wash still counts as a running job
    "goCharging": "returning",
    "returning": "returning",
    "goHome": "returning",
    "pause": "paused",
}
STATION_NAMES = {
    StationState.IDLE: "idle",
    StationState.EMPTYING_DUSTBIN: "emptying",
    StationState.WASHING_MOP: "washing",
    StationState.DRYING_MOP: "drying",
}

from errors import describe  # noqa: E402


class NotConfigured(Exception):
    pass


class RobotUnreachable(Exception):
    pass


@dataclass
class Config:
    email: str
    country: str
    device_id: str
    user_id: str
    access_token: str

    @classmethod
    def from_env(cls) -> Config:
        try:
            return cls(
                email=os.environ["ROBI_EMAIL"],
                country=os.environ["ROBI_COUNTRY"],
                device_id=os.environ["ROBI_DEVICE_ID"],
                user_id=os.environ["ROBI_USER_ID"],
                access_token=os.environ["ROBI_ACCESS_TOKEN"],
            )
        except KeyError as ex:
            raise NotConfigured(f"Missing {ex.args[0]}; run `uv run login.py`") from ex


class Link:
    """Connection to one robot. Reused while the process (or warm function) lives."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.loop = asyncio.get_running_loop()
        self.session = aiohttp.ClientSession()
        rest = create_rest_config(
            self.session, device_id=cfg.device_id, alpha_2_country=cfg.country
        )
        # Password is never stored; the account token mints short-lived portal tokens.
        self.auth = Authenticator(
            rest,
            cfg.email,
            "",
            account_credentials=AccountCredentials(cfg.access_token, cfg.user_id),
        )
        self.device: Device | None = None
        self.name = "Robot"
        self.rooms: list[dict[str, Any]] = []
        self.floor: dict[str, Any] | None = None  # {mid, name, rooms:[{id, points}]}
        self.rooms_at = 0.0
        self.work_data: dict[str, Any] = {}

    async def _device(self) -> Device:
        if self.device is None:
            devices = await ApiClient(self.auth).get_devices()
            if not devices.mqtt:
                raise NotConfigured("No supported robot on this Ecovacs account")
            info = devices.mqtt[0]
            self.device = Device(info, self.auth)
            self.name = info.api.get("nick") or info.api.get("deviceName") or "Robot"
        return self.device

    async def _run(self, command: Any) -> bool:
        """Execute a command; return whether the robot itself answered."""
        dev = await self._device()
        # _execute_command exposes device_reached, which tells us if it's online.
        result = await dev._execute_command(command)  # noqa: SLF001
        return result.device_reached

    async def _run_all(self, commands: list[Any]) -> bool:
        results = await asyncio.gather(
            *(self._run(c) for c in commands), return_exceptions=True
        )
        for r in results:
            if isinstance(r, AuthenticationError):
                raise r
        return any(r is True for r in results)

    # -- status --------------------------------------------------------------

    async def status(self) -> dict[str, Any]:
        dev = await self._device()
        caps = dev.capabilities
        commands = [*caps.battery.get, *caps.error.get, *caps.stats.clean.get]
        if caps.station:
            commands += caps.station.state.get
        need_rooms = not self.rooms or time.time() - self.rooms_at > ROOMS_TTL

        # State queries run in order: charge state first, so that "idle" from the
        # clean-info query is read as "docked" while the robot sits on the station.
        async def state_in_order() -> bool:
            reached = False
            for c in caps.state.get:
                reached = await self._run_all([c]) or reached
            return reached

        online_a, online_b, work, pos, robot_state, _ = await asyncio.gather(
            state_in_order(),
            self._run_all(commands),
            self._work_state(dev),
            self._raw("getPos"),
            self._raw("getRobotState"),
            self._load_floor(dev) if need_rooms else asyncio.sleep(0),
        )
        online = online_a or online_b or work is not None
        bus = dev.events

        state = bus.get_last_event(StateEvent)
        battery = bus.get_last_event(BatteryEvent)
        error = bus.get_last_event(ErrorEvent)
        station = bus.get_last_event(StationEvent)
        stats = bus.get_last_event(StatsEvent)

        problem = describe(error.code, error.description) if error else None
        is_error = bool(problem and problem["severity"] == "error")

        state_name = STATE_NAMES.get(state.state, "unknown") if state else "unknown"
        if work:  # more reliable than getCleanInfo on newer models
            state_name = work
        if state_name == "idle" and state and state.state == State.DOCKED:
            state_name = "docked"
        if is_error and state_name in ("idle", "unknown"):
            state_name = "error"

        station_name = STATION_NAMES.get(station.state, "idle") if station else "idle"
        work_station = (self.work_data.get("stationState") or {}).get("state")
        if station_name == "idle" and work_station in ("washing", "drying", "emptying"):
            station_name = work_station

        return {
            "configured": True,
            "online": online,
            "name": self.name,
            "state": state_name,
            "battery": battery.value if battery else None,
            "station": station_name,
            "problem": problem,
            "relocating": bool(robot_state and robot_state.get("isRelocating")),
            "minutes": round(stats.time / 60) if stats and stats.time else None,
            "area": stats.area if stats and stats.area else None,
            "rooms": self.rooms,
            "map": self.floor,
            "positions": self._positions(pos),
        }

    async def _raw(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Send any command by name; return its data, or None if unsupported/failed."""
        try:
            dev = await self._device()
            raw = await dev.execute_command(CustomCommand(name, args))
            body = raw.get("resp", raw).get("body", {})
            return body.get("data") if body.get("code") == 0 else None
        except AuthenticationError:
            raise
        except Exception:  # noqa: BLE001
            return None

    def _positions(self, pos: dict[str, Any] | None) -> dict[str, Any]:
        """Robot and station positions, only when they belong to the shown floor."""
        out: dict[str, Any] = {"robot": None, "station": None}
        if not pos or not self.floor or str(pos.get("mid")) != self.floor["mid"]:
            return out
        bot = pos.get("deebotPos") or {}
        if bot and not bot.get("invalid"):
            out["robot"] = [bot.get("x", 0), -bot.get("y", 0)]
        for c in pos.get("chargePos") or []:
            if not c.get("invalid"):
                out["station"] = [c.get("x", 0), -c.get("y", 0)]
                break
        return out

    async def _load_floor(self, dev: Device) -> None:
        """Load rooms (and, on newer robots, room outlines) for the floor in use.
        While the robot is lost (relocating) no map is "in use", so fall back to
        the map it was on before, then to the first saved map."""
        try:
            floor = await self._floor_v2()
        except AuthenticationError:
            raise
        except Exception:  # noqa: BLE001
            log.debug("Map v2 load failed", exc_info=True)
            floor = None
        if floor:
            self.rooms = floor.pop("room_list")
            self.floor = floor if floor["rooms"] else None
            self.rooms_at = time.time()
            return
        # Older robots: room names only, through the library.
        if dev.capabilities.map:
            await self._run_all(dev.capabilities.map.rooms.get)
            if rooms := dev.events.get_last_event(RoomsEvent):
                self.rooms = [
                    {"id": r.id, "name": r.name.strip() or f"Soba {r.id}"} for r in rooms.rooms
                ]
                self.rooms_at = time.time()

    async def _floor_v2(self) -> dict[str, Any] | None:
        cached, robot_state = await asyncio.gather(
            self._raw("getCachedMapInfo"), self._raw("getRobotState")
        )
        maps = [m for m in (cached or {}).get("info", []) if str(m.get("mid", "0")) != "0"]
        if not maps:
            return None
        chosen = next((m for m in maps if m.get("using")), None)
        prev = str((robot_state or {}).get("prevMidRelocating") or "0")
        if chosen is None and prev != "0":
            chosen = next((m for m in maps if str(m["mid"]) == prev), None)
        if chosen is None:
            chosen = next((m for m in maps if m.get("built")), maps[0])
        mid = str(chosen["mid"])

        rooms_data, info_data = await asyncio.gather(
            self._raw("getMapSet_V2", {"mid": mid, "type": "ar"}),
            self._raw("getMapInfo_V2", {"mid": mid, "type": "0"}),
        )
        if not rooms_data or not isinstance(rooms_data.get("subsets"), str):
            return None
        subsets = json.loads(decompress_base64_data(rooms_data["subsets"]).decode())
        room_list = []
        centers: dict[int, tuple[float, float]] = {}
        for sub in subsets:
            rid = int(sub[0])
            icon = int(sub[2]) if sub[2].isdigit() else -1
            name = sub[1].strip() or ROOM_ICON_NAMES.get(icon, f"Soba {rid}")
            room_list.append({"id": rid, "name": name})
            try:
                centers[rid] = (float(sub[5]), -float(sub[6]))
            except (IndexError, ValueError):
                pass

        outlines = _room_outlines(info_data)
        shapes = []
        for idx, room in enumerate(room_list):
            c = centers.get(room["id"])
            poly = next((p for p in outlines if c and _inside(c, p)), None)
            if poly is None and idx < len(outlines) and len(outlines) == len(room_list):
                poly = outlines[idx]
            if poly:
                shapes.append({"id": room["id"], "points": poly, "label": c})
        return {"mid": mid, "name": chosen.get("name") or "", "rooms": shapes, "room_list": room_list}

    async def _work_state(self, dev: Device) -> str | None:
        """Ask getWorkState, which newer robots (e.g. this one) answer truthfully
        while getCleanInfo_V2 keeps saying "idle". Returns None if unsupported."""
        data = None
        for _ in range(2):  # one retry: the first call on a cold start can time out
            try:
                raw = await dev.execute_command(CustomCommand("getWorkState"))
                body = raw.get("resp", raw)["body"]
                if body.get("code") == 20003:  # "rcp not support": older model
                    return None
                if body.get("code") == 0:
                    data = body["data"]
                    break
            except Exception:  # noqa: BLE001
                pass
        if data is None:
            return None
        self.work_data = data
        robot_state = (data.get("robotState") or {}).get("state", "")
        if data.get("paused"):
            return "paused"
        return WORK_STATES.get(robot_state, "idle" if robot_state == "idle" else None)

    # -- commands ------------------------------------------------------------

    async def _sync_state(self, dev: Device) -> str:
        """Tell the library the real state before a command. Its Clean command
        rewrites start<->resume based on the state it believes, and on this model
        that belief comes from getCleanInfo_V2, which always says "idle"."""
        await self._run_all(dev.capabilities.state.get)
        last = dev.events.get_last_event(StateEvent)
        work = await self._work_state(dev)
        believed = {
            "cleaning": State.CLEANING, "paused": State.PAUSED,
            "returning": State.RETURNING, "idle": State.IDLE,
        }.get(work or "", last.state if last else State.IDLE)
        if last and last.state == State.DOCKED and believed == State.IDLE:
            believed = State.DOCKED
        dev.events.notify(StateEvent(believed))
        await asyncio.sleep(0)  # let the bus record it
        return STATE_NAMES.get(believed, "unknown")

    async def clean_rooms(self, room_ids: list[int]) -> None:
        dev = await self._device()
        area = dev.capabilities.clean.action.area
        if area is None:
            raise ValueError("Ovaj robot ne podržava čišćenje po sobama.")
        if await self._sync_state(dev) == "paused":
            # starting fresh while paused would be turned into "resume"; end the old job
            await self._command(dev.capabilities.clean.action.command(CleanAction.STOP))
            dev.events.notify(StateEvent(State.IDLE))
            await asyncio.sleep(0)
        await self._command(area(CleanMode.SPOT_AREA, room_ids, 1))

    async def pause(self) -> None:
        dev = await self._device()
        await self._sync_state(dev)
        await self._command(dev.capabilities.clean.action.command(CleanAction.PAUSE))

    async def resume(self) -> None:
        dev = await self._device()
        if await self._sync_state(dev) != "paused":
            return  # never let "resume" turn into a whole-house clean
        await self._command(dev.capabilities.clean.action.command(CleanAction.RESUME))

    async def go_home(self) -> None:
        """Same as "End and Dock" in the Ecovacs app."""
        dev = await self._device()
        caps = dev.capabilities
        if await self._sync_state(dev) in ("cleaning", "paused"):
            await self._command(caps.clean.action.command(CleanAction.STOP))
        await self._command(caps.charge.execute())

    async def refresh_rooms(self) -> None:
        self.rooms_at = 0

    async def _command(self, command: Any) -> None:
        if not await self._run(command):
            raise RobotUnreachable()

    async def close(self) -> None:
        await self.auth.teardown()
        await self.session.close()


_link: Link | None = None


async def get_link() -> Link:
    """One Link per process and event loop."""
    global _link
    if _link is None or _link.loop is not asyncio.get_running_loop():
        _link = Link(Config.from_env())
    return _link


async def reset_link() -> None:
    global _link
    if _link is not None:
        try:
            await _link.close()
        except Exception:  # noqa: BLE001
            pass
    _link = None


def _room_outlines(info_data: dict[str, Any] | None) -> list[list[list[int]]]:
    """Room outlines from getMapInfo_V2: a compressed list of layers; the layer
    starting with "1" holds one "index;x,y,flag;x,y,flag;..." string per room.
    y is flipped so the map shows the same way round as in the Ecovacs app."""
    if not info_data or not isinstance(info_data.get("info"), str):
        return []
    layers = json.loads(decompress_base64_data(info_data["info"]).decode())
    layer = next((l for l in layers if isinstance(l, list) and l and str(l[0]) == "1"), None)
    out = []
    for entry in (layer or [])[1:]:
        pts = []
        for tok in str(entry).split(";")[1:]:
            parts = tok.split(",")
            if len(parts) >= 2:
                try:
                    pts.append([int(float(parts[0])), -int(float(parts[1]))])
                except ValueError:
                    pass
        if len(pts) >= 3:
            out.append(pts)
    return out


def _inside(point: tuple[float, float], poly: list[list[int]]) -> bool:
    x, y = point
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside
