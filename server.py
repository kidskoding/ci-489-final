"""Relay server for Kepler Path multiplayer."""
from __future__ import annotations

import asyncio
import http
import json
import os
import socket
import threading

import websockets

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 3000))
DISCOVERY_PORT = 48901
JOIN_CODE = "CI-489-DEMO"

# roomCode -> set of connected clients
rooms: dict[str, set] = {}


def room_players(room_code: str) -> list[str]:
    if room_code not in rooms:
        return []
    return [
        ws.player_name
        for ws in rooms[room_code]
        if getattr(ws, "player_name", None)
    ]


def unique_player_name(room_code: str, requested: str, ws) -> str:
    base = (requested or "Player").strip() or "Player"
    existing = set(room_players(room_code)) - {getattr(ws, "player_name", None)}
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


async def broadcast(room_code: str, message: dict, exclude=None) -> None:
    if room_code not in rooms:
        return
    payload = json.dumps(message)
    targets = [ws for ws in rooms[room_code] if ws is not exclude]
    if targets:
        await asyncio.gather(*[ws.send(payload) for ws in targets], return_exceptions=True)


async def broadcast_roster(room_code: str) -> None:
    await broadcast(room_code, {"type": "players", "players": room_players(room_code)[:4]})


async def handler(ws) -> None:
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
                current_room = str(msg.get("room", JOIN_CODE)).strip()[:64] or JOIN_CODE
                if current_room not in rooms:
                    rooms[current_room] = set()
                rooms[current_room].add(ws)
                await ws.send(json.dumps({"type": "players", "players": room_players(current_room)[:4]}))

            elif msg_type == "hello":
                if current_room is None:
                    continue
                name = unique_player_name(current_room, msg.get("name", "Player"), ws)
                ws.player_name = name
                await ws.send(json.dumps({"type": "hello_ack", "name": name}))
                await broadcast_roster(current_room)

            else:
                if current_room and current_room in rooms:
                    await broadcast(current_room, msg, exclude=ws)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if current_room and current_room in rooms:
            rooms[current_room].discard(ws)
            if rooms[current_room]:
                await broadcast_roster(current_room)
            else:
                del rooms[current_room]


def run_discovery() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", DISCOVERY_PORT))
        sock.settimeout(1.0)
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                text = data.decode("utf-8", errors="ignore")
                if text == f"HOLOORBIT_DISCOVER:{JOIN_CODE}":
                    response = f"HOLOORBIT_HOST:{JOIN_CODE}:{PORT}".encode()
                    sock.sendto(response, addr)
            except socket.timeout:
                continue
    except OSError as e:
        print(f"Discovery disabled: {e}")
    finally:
        sock.close()


async def health_check(connection, request):
    if request.path == "/healthz":
        return connection.respond(http.HTTPStatus.OK, '{"ok":true}')
    return None


async def main() -> None:
    threading.Thread(target=run_discovery, daemon=True).start()
    async with websockets.serve(handler, HOST, PORT, process_request=health_check):
        print(f"Kepler relay server running on ws://{HOST}:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
