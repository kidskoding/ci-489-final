import asyncio

from game import KeplerGame


async def main():
    game = KeplerGame("menu", "127.0.0.1:3000", 3000, "Player")
    await game.run()


asyncio.run(main())
