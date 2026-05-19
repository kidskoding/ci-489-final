import asyncio
import pygame

async def main():
    pygame.init()
    screen = pygame.display.set_mode((1024, 579))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 48)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        screen.fill((0, 100, 200))
        label = font.render("pygame works!", True, (255, 255, 255))
        screen.blit(label, (300, 250))
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()

asyncio.run(main())
