import asyncio
import argparse
import pygame

RELAY = "ci-489-final.onrender.com"


def is_browser_runtime() -> bool:
    try:
        import platform
        return hasattr(platform, "window")
    except Exception:
        return False


async def main():
    parser = argparse.ArgumentParser(description="Kepler Path")
    parser.add_argument("--host-session", action="store_true", help="Host a local Python multiplayer session")
    parser.add_argument("--join", metavar="HOST", help="Join a local Python multiplayer session")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--name", default="Player")
    args, _ = parser.parse_known_args()

    pygame.init()
    screen = pygame.display.set_mode((1024, 579))

    try:
        from game import KeplerGame

        mode = "menu"
        host = RELAY if is_browser_runtime() else f"127.0.0.1:{args.port}"
        if args.host_session:
            mode = "host"
        elif args.join:
            mode = "join"
            host = args.join
            if ":" not in host:
                host = f"{host}:{args.port}"

        game = KeplerGame(mode, host, args.port, args.name)
        await game.run()
    except Exception:
        import traceback
        err = traceback.format_exc()
        font = pygame.font.SysFont("arial", 18)
        screen.fill((120, 0, 0))
        for i, line in enumerate(err.split("\n")[:24]):
            screen.blit(font.render(line[:90], True, (255, 255, 255)), (10, 10 + i * 22))
        pygame.display.flip()
        while True:
            await asyncio.sleep(1)


asyncio.run(main())
