"""Robi: a tiny web app for cleaning chosen rooms with an Ecovacs Deebot.

Locally:   uv run app.py            (reads .env.local, made by `uv run login.py`)
Demo:      ROBI_DEMO=1 uv run app.py
Vercel:    deployed as a FastAPI function; settings come from env vars.

Every /api call needs the secret key (ROBI_KEY), which the phone gets once
from the link  https://<host>/#k=<key>  and then remembers.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import os
import random
import socket
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


load_env_file(ROOT / ".env.local")

DEMO = os.environ.get("ROBI_DEMO") == "1"
KEY = "demo" if DEMO else os.environ.get("ROBI_KEY", "")

import robot  # noqa: E402  (after env is loaded)
from errors import describe  # noqa: E402

log = logging.getLogger("robi")
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def require_key(x_robi_key: str = Header(default="")) -> None:
    if not KEY:
        raise HTTPException(503, "ROBI_KEY nije postavljen na serveru.")
    if not hmac.compare_digest(x_robi_key.encode(), KEY.encode()):
        raise HTTPException(401, "Neispravan ključ. Otvori poveznicu koju si dobio.")


class CleanBody(BaseModel):
    rooms: list[int]


# ---------------------------------------------------------------- demo robot


class Demo:
    def __init__(self) -> None:
        self.s: dict[str, Any] = {
            "configured": True, "online": True, "name": "Robi (demo)", "state": "docked",
            "battery": 100, "station": "idle", "problem": None,
            "minutes": None, "area": None, "relocating": False,
            "map": {"mid": "demo", "name": "Prizemlje (demo)", "rooms": [
                {"id": i, "points": pts, "label": None} for i, pts in enumerate([
                    [[4000, 2000], [9000, 2000], [9000, 7000], [4000, 7000]],        # living
                    [[0, -2000], [4000, -2000], [4000, 1000], [0, 1000]],            # kitchen
                    [[4000, -3000], [9000, -3000], [9000, 2000], [4000, 2000]],      # dining
                    [[-5000, -3000], [-1000, -3000], [-1000, 1000], [-5000, 1000]],  # bedroom
                    [[-5000, 3000], [-1000, 3000], [-1000, 7000], [-5000, 7000]],    # kids
                    [[0, 3000], [2500, 3000], [2500, 7000], [0, 7000]],              # bath
                    [[-5000, 1000], [4000, 1000], [4000, 3000], [-5000, 3000]],      # corridor
                ])]},
            "positions": {"robot": None, "station": [3700, 1500]},
            "rooms": [
                {"id": i, "name": n}
                for i, n in enumerate(["Living room", "Kitchen", "Dining room", "Bedroom",
                                       "Kids room", "Bathroom", "Corridor"])
            ],
        }

    async def _later(self, delay: float, **changes: Any) -> None:
        await asyncio.sleep(delay)
        self.s.update(changes)

    async def status(self) -> dict[str, Any]:
        return self.s

    async def clean_rooms(self, rooms: list[int]) -> None:
        self.s.update(state="cleaning", battery=random.randint(70, 99), minutes=3, area=4)
        room = next(r for r in self.s["map"]["rooms"] if r["id"] == rooms[0])
        xs = [p[0] for p in room["points"]]; ys = [p[1] for p in room["points"]]
        self.s["positions"] = {**self.s["positions"], "robot": [sum(xs) / 4, sum(ys) / 4]}
        if 5 in rooms:  # picking the bathroom shows what an error looks like
            asyncio.create_task(self._later(3, state="paused", problem=describe(109)))

    async def pause(self) -> None:
        self.s["state"] = "paused"

    async def resume(self) -> None:
        self.s.update(state="cleaning", problem=None)

    async def go_home(self) -> None:
        self.s.update(state="returning", problem=None, minutes=None, area=None)
        asyncio.create_task(self._later(4, positions={"robot": None, "station": [3700, 1500]}))
        asyncio.create_task(self._later(4, state="docked", station="emptying"))
        asyncio.create_task(self._later(10, station="washing"))
        asyncio.create_task(self._later(16, station="idle"))

    async def refresh_rooms(self) -> None:
        pass


_demo = Demo() if DEMO else None


async def link() -> Any:
    return _demo or await robot.get_link()


# ---------------------------------------------------------------- routes


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "public" / "index.html")


@app.exception_handler(robot.NotConfigured)
async def not_configured(_: Any, ex: robot.NotConfigured) -> JSONResponse:
    return JSONResponse({"configured": False, "message": str(ex)})


async def guarded(action: str, *args: Any) -> dict[str, Any]:
    """Run a robot call and turn failures into messages the page can show."""
    try:
        r = await link()
        if action != "status":
            await getattr(r, action)(*args)
        return await r.status()
    except robot.NotConfigured:
        raise
    except robot.RobotUnreachable:
        raise HTTPException(503, "Robot ne odgovara. Je li uključen i spojen na Wi-Fi?")
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    except robot.AuthenticationError:
        await robot.reset_link()
        raise HTTPException(
            401, "Prijava u Ecovacs je istekla. Treba ponovno pokrenuti login.py.")
    except Exception as ex:
        log.exception("Robot call %s failed", action)
        await robot.reset_link()
        raise HTTPException(502, f"Ecovacs ne odgovara ({type(ex).__name__}). Pokušaj ponovno.")


@app.get("/api/status", dependencies=[Depends(require_key)])
async def status() -> dict[str, Any]:
    return await guarded("status")


@app.post("/api/clean", dependencies=[Depends(require_key)])
async def clean(body: CleanBody) -> dict[str, Any]:
    if not body.rooms:
        raise HTTPException(400, "Odaberi barem jednu sobu.")
    return await guarded("clean_rooms", body.rooms)


@app.post("/api/pause", dependencies=[Depends(require_key)])
async def pause() -> dict[str, Any]:
    return await guarded("pause")


@app.post("/api/resume", dependencies=[Depends(require_key)])
async def resume() -> dict[str, Any]:
    return await guarded("resume")


@app.post("/api/home", dependencies=[Depends(require_key)])
async def home() -> dict[str, Any]:
    return await guarded("go_home")


@app.post("/api/refresh", dependencies=[Depends(require_key)])
async def refresh() -> dict[str, Any]:
    return await guarded("refresh_rooms")


# ---------------------------------------------------------------- local run


def lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "localhost"


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("ROBI_PORT", "8080"))
    print(f"\n  Robi is running{' (DEMO)' if DEMO else ''}. Open on your phone:")
    print(f"    http://{lan_ip()}:{port}/#k={KEY}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
