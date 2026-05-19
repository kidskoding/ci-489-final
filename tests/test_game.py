import os
import pytest
import pygame

# Use dummy video driver for headless testing
os.environ["SDL_VIDEODRIVER"] = "dummy"

from game import KeplerGame, NetworkSession

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


def test_network_session_can_be_constructed_before_event_loop():
    session = NetworkSession("host", "127.0.0.1", 3000, "Host")

    assert session.status == "Waiting for event loop"
    assert session.normalize_host("127.0.0.1") == "127.0.0.1:3000"
    assert session.normalize_host("ws://127.0.0.1:3000/") == "127.0.0.1:3000"

    session.close()

def test_network_session_applies_server_assigned_unique_name():
    session = NetworkSession("host", "127.0.0.1", 3000, "Player")
    session._handle_message({"type": "hello_ack", "name": "Player 2"})

    assert session.name == "Player 2"

    session.close()

def test_law_modes_track_learning_progress():
    game = KeplerGame(multiplayer_mode="solo")

    game.open_terminal(game.terminal_named("Law 1 Lab"))
    assert game.mode == "law1"
    game.adjust_orbit_shape(220)
    assert game.lesson_success == True

    game.open_terminal(game.terminal_named("Law 2 Lab"))
    assert game.mode == "law2"
    game.capture_equal_time_area()
    game.t = 0.45
    game.capture_equal_time_area()
    assert len(game.area_captures) == 2
    assert game.lesson_success == True

    game.open_terminal(game.terminal_named("Law 3 Lab"))
    assert game.mode == "law3"
    game.select_law3_preset(1)
    assert game.lesson_success == True

    pygame.quit()

def test_interactive_tutorial_records_measurement_and_progresses():
    game = KeplerGame(multiplayer_mode="solo")
    game.open_terminal(game.terminal_named("Training Sim"))

    red_dwarf_pos = game.world_to_screen(game.bodies()["Red Dwarf"].pos)
    perihelion_pos = game.world_to_screen(game.bodies()["Perihelion"].pos)

    game.handle_click(red_dwarf_pos)
    assert game.tutorial_step == 1
    game.handle_click(perihelion_pos)
    assert game.tutorial_step == 2
    assert len(game.measurements) == 1

    pygame.quit()
