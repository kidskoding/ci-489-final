import asyncio

from game import KeplerGame

RELAY = "ci-489-final.onrender.com"


async def main():
    game = KeplerGame("menu", RELAY, 3000, "Player")
    await game.run()


asyncio.run(main())
