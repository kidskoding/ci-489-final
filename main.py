import asyncio
import pygame

RELAY = "ci-489-final.onrender.com"


async def main():
    pygame.init()
    screen = pygame.display.set_mode((1024, 579))

    try:
        from game import KeplerGame
        game = KeplerGame("menu", RELAY, 3000, "Player")
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
