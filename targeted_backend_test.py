#!/usr/bin/env python3
import requests
import json
import time
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import random

# Load environment variables from frontend/.env to get the backend URL
load_dotenv(Path(__file__).parent / "frontend" / ".env")

# Get the backend URL from environment variables
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND_URL:
    print("Error: REACT_APP_BACKEND_URL not found in environment variables")
    sys.exit(1)

# Ensure the URL ends with /api
API_URL = f"{BACKEND_URL}/api"
print(f"Using API URL: {API_URL}")

class TargetedBackendTest:
    def __init__(self):
        self.game_id = None
        self.game_state = None
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0
        }
    
    def assert_test(self, condition, test_name, details=""):
        """Helper method to track test results"""
        self.test_results["total_tests"] += 1
        if condition:
            self.test_results["passed_tests"] += 1
            print(f"✅ PASS: {test_name}")
            return True
        else:
            self.test_results["failed_tests"] += 1
            print(f"❌ FAIL: {test_name}")
            if details:
                print(f"    Details: {details}")
            return False
    
    def create_new_game(self):
        """Create a new game"""
        print("\n=== Creating New Game ===")
        response = requests.post(f"{API_URL}/game/new")
        
        # Check response status
        if response.status_code != 200:
            print(f"Error creating game: {response.status_code}")
            return False
        
        # Parse response
        try:
            data = response.json()
            self.game_id = data.get("id")
            self.game_state = data
            print(f"Created game with ID: {self.game_id}")
            return True
        except Exception as e:
            print(f"Error parsing game creation response: {str(e)}")
            return False
    
    def make_move(self, x, y):
        """Make a move in the game"""
        if not self.game_id:
            print("No game ID available")
            return False
        
        move_data = {
            "game_id": self.game_id,
            "x": x,
            "y": y
        }
        
        response = requests.post(f"{API_URL}/game/move", json=move_data)
        
        # Check response status
        if response.status_code != 200:
            print(f"Error making move: {response.status_code}")
            return False
        
        # Parse response
        try:
            data = response.json()
            if not data.get("success"):
                print(f"Move failed: {data.get('message')}")
                return False
            
            # Update game state
            self.game_state = data.get("game_state")
            return data
        except Exception as e:
            print(f"Error parsing move response: {str(e)}")
            return False
    
    def print_grid(self):
        """Print the current grid state for debugging"""
        if not self.game_state:
            print("No game state available")
            return
        
        grid = self.game_state.get("grid", [])
        print("\nCurrent Grid:")
        for row in grid:
            print(" ".join([f"{cell:3d}" for cell in row]))
        print()
    
    def test_bear_trapping_logic(self):
        """
        Test that bears are properly trapped when surrounded.
        Create a scenario where a bear is completely surrounded by items
        and verify it transforms into a tombstone.
        """
        print("\n=== Testing Bear Trapping Logic ===")
        
        # Create a new game
        if not self.create_new_game():
            return False
        
        # First, we need to place a bear on the board
        # Since bears only spawn after move 10 and with probability,
        # we'll use a specific pattern to try to create a controlled scenario
        
        # Make 15 moves to increase bear spawn chance
        print("Making initial moves to increase bear spawn chance...")
        for i in range(15):
            # Find an empty spot
            move_made = False
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -99:  # Empty
                        self.make_move(x, y)
                        move_made = True
                        break
                if move_made:
                    break
        
        # Find a bear on the board
        bear_x, bear_y = None, None
        for x in range(6):
            for y in range(6):
                if self.game_state["grid"][x][y] == -1:  # Bear
                    bear_x, bear_y = x, y
                    break
            if bear_x is not None:
                break
        
        if bear_x is None:
            print("No bears found on the board. Creating a new game and trying again...")
            # Try again with a new game
            if not self.create_new_game():
                return False
            
            # Make more moves to increase bear spawn chance
            for i in range(20):
                move_made = False
                for x in range(6):
                    for y in range(6):
                        if self.game_state["grid"][x][y] == -99:  # Empty
                            self.make_move(x, y)
                            move_made = True
                            break
                    if move_made:
                        break
            
            # Find a bear again
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -1:  # Bear
                        bear_x, bear_y = x, y
                        break
                if bear_x is not None:
                    break
        
        if bear_x is None:
            self.assert_test(False, "Bear Trapping Logic", "Could not find a bear on the board after multiple attempts")
            return False
        
        print(f"Found bear at position ({bear_x}, {bear_y})")
        self.print_grid()
        
        # Now we need to surround the bear with items
        # We'll try to place items in all adjacent cells
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        surrounding_cells = []
        
        # Identify all surrounding cells that are within bounds
        for dx, dy in directions:
            nx, ny = bear_x + dx, bear_y + dy
            if 0 <= nx < 6 and 0 <= ny < 6:
                surrounding_cells.append((nx, ny))
        
        print(f"Attempting to surround bear with items at {surrounding_cells}")
        
        # Place items in all surrounding cells
        for nx, ny in surrounding_cells:
            if self.game_state["grid"][nx][ny] == -99:  # Empty
                print(f"Placing item at ({nx}, {ny})")
                self.make_move(nx, ny)
                
                # Check if bear turned into tombstone after this move
                if self.game_state["grid"][bear_x][bear_y] == -2:  # Tombstone
                    print("Bear transformed into tombstone!")
                    self.print_grid()
                    self.assert_test(True, "Bear Trapping Logic", "Bear correctly transformed into tombstone when surrounded")
                    return True
        
        # After placing items in all surrounding cells, check if bear turned into tombstone
        if self.game_state["grid"][bear_x][bear_y] == -2:  # Tombstone
            print("Bear transformed into tombstone!")
            self.print_grid()
            self.assert_test(True, "Bear Trapping Logic", "Bear correctly transformed into tombstone when surrounded")
            return True
        else:
            print("Bear did not transform into tombstone despite being surrounded")
            self.print_grid()
            self.assert_test(False, "Bear Trapping Logic", "Bear did not transform into tombstone when surrounded")
            return False
    
    def test_game_over_detection(self):
        """
        Test the game over functionality by filling the entire 6x6 board
        and verifying that the game_over flag is set to true.
        """
        print("\n=== Testing Game Over Detection ===")
        
        # Create a new game
        if not self.create_new_game():
            return False
        
        # Fill the entire board systematically
        print("Filling the board to trigger game over...")
        
        # First, count how many empty cells we have
        empty_count = sum(row.count(-99) for row in self.game_state["grid"])
        print(f"Starting with {empty_count} empty cells")
        
        # Fill all empty cells
        moves_made = 0
        for x in range(6):
            for y in range(6):
                if self.game_state["grid"][x][y] == -99:  # Empty
                    print(f"Placing item at ({x}, {y})")
                    result = self.make_move(x, y)
                    if not result:
                        print(f"Failed to make move at ({x}, {y})")
                        continue
                    
                    moves_made += 1
                    
                    # Check if game over after each move
                    if self.game_state["game_over"]:
                        print(f"Game over detected after {moves_made} moves!")
                        self.print_grid()
                        self.assert_test(True, "Game Over Detection", "Game over flag correctly set to true when board is full")
                        return True
        
        # After filling all cells, check if game over is detected
        empty_count = sum(row.count(-99) for row in self.game_state["grid"])
        print(f"Ending with {empty_count} empty cells")
        
        if self.game_state["game_over"]:
            print("Game over detected after filling the board!")
            self.assert_test(True, "Game Over Detection", "Game over flag correctly set to true when board is full")
            return True
        else:
            print("Game over not detected despite filling the board")
            self.print_grid()
            self.assert_test(False, "Game Over Detection", "Game over flag not set to true when board is full")
            return False
    
    def run_targeted_tests(self):
        """Run the targeted tests for the fixed issues"""
        print("\n===== TARGETED BACKEND API TESTS =====")
        
        # Test the bear trapping logic
        self.test_bear_trapping_logic()
        
        # Test the game over detection
        self.test_game_over_detection()
        
        # Print test summary
        print("\n===== TEST SUMMARY =====")
        print(f"Total tests: {self.test_results['total_tests']}")
        print(f"Passed: {self.test_results['passed_tests']}")
        print(f"Failed: {self.test_results['failed_tests']}")
        
        if self.test_results['failed_tests'] == 0:
            print("\n✅ ALL TESTS PASSED!")
        else:
            print(f"\n❌ {self.test_results['failed_tests']} TESTS FAILED!")
        
        return self.test_results['failed_tests'] == 0

if __name__ == "__main__":
    tester = TargetedBackendTest()
    success = tester.run_targeted_tests()
    sys.exit(0 if success else 1)