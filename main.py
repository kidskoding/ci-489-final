import asyncio
import pygame

RELAY = "ci-489-final.onrender.com"


def draw_error(screen, msg):
    font = pygame.font.SysFont("arial", 20)
    screen.fill((120, 0, 0))
    for i, line in enumerate(msg.split("\n")[:24]):
        surf = font.render(line[:90], True, (255, 255, 255))
        screen.blit(surf, (10, 10 + i * 24))
    pygame.display.flip()


async def main():
    print("main: start")
    pygame.init()
    screen = pygame.display.set_mode((1024, 579))

    try:
        from game import KeplerGame
        print("main: KeplerGame imported")
    except Exception:
        import traceback
        draw_error(screen, traceback.format_exc())
        while True:
            await asyncio.sleep(1)
        return

    try:
        print("main: creating game")
        game = KeplerGame("menu", RELAY, 3000, "Player")
        print("main: running")
        await game.run()
    except Exception:
        import traceback
        err = traceback.format_exc()
        print(err)
        draw_error(screen, err)
        while True:
            await asyncio.sleep(1)


asyncio.run(main())
