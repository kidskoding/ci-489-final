import asyncio
import sys

print("main.py: start", flush=True)

try:
    from game import KeplerGame
    print("main.py: KeplerGame imported", flush=True)
except Exception as e:
    print(f"main.py: import error: {e}", flush=True)
    sys.exit(1)


async def main():
    print("main.py: creating game", flush=True)
    try:
        game = KeplerGame("menu", "127.0.0.1:3000", 3000, "Player")
        print("main.py: game created, running", flush=True)
        await game.run()
    except Exception as e:
        print(f"main.py: game error: {e}", flush=True)
        import traceback
        traceback.print_exc()


asyncio.run(main())
