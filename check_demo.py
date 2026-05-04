import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game import demo_check


if __name__ == "__main__":
    print(demo_check())
