import os
import pytest
import pygame

# Use dummy video driver for headless testing
os.environ["SDL_VIDEODRIVER"] = "dummy"

from game import KeplerGame

def test_game_initialization():
    game = KeplerGame(multiplayer_mode="solo")
    assert game.screen_state == "ship"
    assert game.mode == "play"
    assert len(game.crew) == 4
    assert game.running == True

def test_demo_logic():
    # Similar to demo_check in game.py
    game = KeplerGame(multiplayer_mode="solo")
    game.update(1 / 60)
    
    assert game.screen_state == "ship"
    
    # Switch to orbit/measure mode
    game.screen_state = "orbit"
    game.mode = "measure"
    
    # Mock some clicks to record a measurement
    # We need to find valid click targets (bodies)
    bodies = game.bodies()
    red_dwarf_pos = game.world_to_screen(bodies["Red Dwarf"].pos)
    perihelion_pos = game.world_to_screen(bodies["Perihelion"].pos)
    
    game.handle_click(red_dwarf_pos)
    game.handle_click(perihelion_pos)
    
    assert len(game.measurements) == 1
    assert game.measurements[0].distance > 0
    
    pygame.quit()
