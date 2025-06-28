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
        
        This test uses a more controlled approach by checking after each move
        if a bear is in a position where it can be trapped in the next move.
        """
        print("\n=== Testing Bear Trapping Logic ===")
        
        # Create a new game
        if not self.create_new_game():
            return False
        
        # Make moves until we have a bear that's almost trapped
        max_attempts = 50
        attempt = 0
        bear_trapped = False
        
        print("Making moves to find and trap a bear...")
        while attempt < max_attempts and not bear_trapped:
            attempt += 1
            
            # Make a move
            move_made = False
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -99:  # Empty
                        self.make_move(x, y)
                        move_made = True
                        break
                if move_made:
                    break
            
            if not move_made:
                print("No empty cells left to make a move")
                break
            
            # After each move, check if there's a bear that can be trapped
            # by placing one more item
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -1:  # Bear
                        # Check if this bear has only one empty adjacent cell
                        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                        empty_neighbors = []
                        
                        for dx, dy in directions:
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < 6 and 0 <= ny < 6:
                                if self.game_state["grid"][nx][ny] == -99:  # Empty
                                    empty_neighbors.append((nx, ny))
                        
                        # If there's only one empty neighbor, we can trap the bear
                        if len(empty_neighbors) == 1:
                            print(f"Found bear at ({x}, {y}) with only one escape route at {empty_neighbors[0]}")
                            self.print_grid()
                            
                            # Place an item in the last empty neighbor to trap the bear
                            nx, ny = empty_neighbors[0]
                            print(f"Placing item at ({nx}, {ny}) to trap the bear")
                            self.make_move(nx, ny)
                            
                            # Check if the bear turned into a tombstone
                            if self.game_state["grid"][x][y] == -2:  # Tombstone
                                print("Bear transformed into tombstone!")
                                self.print_grid()
                                self.assert_test(True, "Bear Trapping Logic", 
                                                "Bear correctly transformed into tombstone when surrounded")
                                bear_trapped = True
                                return True
                            else:
                                print(f"Bear at ({x}, {y}) did not transform into tombstone despite being surrounded")
                                self.print_grid()
        
        # If we couldn't trap a bear after max_attempts, try a more direct approach
        if not bear_trapped:
            print(f"Could not trap a bear after {max_attempts} attempts. Trying a different approach...")
            
            # Create a new game
            if not self.create_new_game():
                return False
            
            # Make at least 15 moves to increase bear spawn chance
            for i in range(15):
                for x in range(6):
                    for y in range(6):
                        if self.game_state["grid"][x][y] == -99:  # Empty
                            self.make_move(x, y)
                            break
                    else:
                        continue
                    break
            
            # Look for any bears on the board
            bears_found = []
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -1:  # Bear
                        bears_found.append((x, y))
            
            if not bears_found:
                self.assert_test(False, "Bear Trapping Logic", "Could not find any bears on the board")
                return False
            
            # Try to trap each bear by filling all adjacent cells
            for bear_x, bear_y in bears_found:
                print(f"Attempting to trap bear at ({bear_x}, {bear_y})")
                self.print_grid()
                
                # Get all empty adjacent cells
                directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                empty_neighbors = []
                
                for dx, dy in directions:
                    nx, ny = bear_x + dx, bear_y + dy
                    if 0 <= nx < 6 and 0 <= ny < 6:
                        if self.game_state["grid"][nx][ny] == -99:  # Empty
                            empty_neighbors.append((nx, ny))
                
                # Fill all empty neighbors
                for nx, ny in empty_neighbors:
                    print(f"Placing item at ({nx}, {ny})")
                    self.make_move(nx, ny)
                    
                    # Check if bear turned into tombstone
                    if self.game_state["grid"][bear_x][bear_y] == -2:  # Tombstone
                        print("Bear transformed into tombstone!")
                        self.print_grid()
                        self.assert_test(True, "Bear Trapping Logic", 
                                        "Bear correctly transformed into tombstone when surrounded")
                        return True
                    
                    # If the bear moved, update its position
                    if self.game_state["grid"][bear_x][bear_y] != -1:
                        # Look for the bear again
                        new_bear_pos = None
                        for x in range(6):
                            for y in range(6):
                                if self.game_state["grid"][x][y] == -1:  # Bear
                                    new_bear_pos = (x, y)
                                    break
                            if new_bear_pos:
                                break
                        
                        if new_bear_pos:
                            bear_x, bear_y = new_bear_pos
                            print(f"Bear moved to ({bear_x}, {bear_y})")
                            
                            # Recalculate empty neighbors
                            empty_neighbors = []
                            for dx, dy in directions:
                                nx, ny = bear_x + dx, bear_y + dy
                                if 0 <= nx < 6 and 0 <= ny < 6:
                                    if self.game_state["grid"][nx][ny] == -99:  # Empty
                                        empty_neighbors.append((nx, ny))
            
            # Check if any bear turned into a tombstone
            tombstone_found = False
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -2:  # Tombstone
                        tombstone_found = True
                        break
                if tombstone_found:
                    break
            
            if tombstone_found:
                print("Found a tombstone on the board!")
                self.print_grid()
                self.assert_test(True, "Bear Trapping Logic", "Bear correctly transformed into tombstone when surrounded")
                return True
        
        self.assert_test(False, "Bear Trapping Logic", "Could not trap a bear after multiple attempts")
        return False
    
    def test_game_over_detection(self):
        """
        Test the game over functionality by filling the entire 6x6 board
        and verifying that the game_over flag is set to true.
        
        This test uses a more systematic approach to ensure all cells are filled.
        """
        print("\n=== Testing Game Over Detection ===")
        
        # Create a new game
        if not self.create_new_game():
            return False
        
        # Fill the board systematically, focusing on one cell at a time
        print("Filling the board to trigger game over...")
        
        # Keep track of how many moves we've made
        moves_made = 0
        max_moves = 100  # Safety limit
        
        while moves_made < max_moves:
            # Count empty cells
            empty_cells = []
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -99:  # Empty
                        empty_cells.append((x, y))
            
            empty_count = len(empty_cells)
            print(f"Current empty cells: {empty_count}")
            
            if empty_count == 0:
                # Board is full, check game over
                if self.game_state["game_over"]:
                    print("Game over detected when board is full!")
                    self.print_grid()
                    self.assert_test(True, "Game Over Detection", 
                                    "Game over flag correctly set to true when board is full")
                    return True
                else:
                    print("Board is full but game_over flag is not set to true")
                    self.print_grid()
                    self.assert_test(False, "Game Over Detection", 
                                    "Game over flag not set to true when board is full")
                    return False
            
            # Make a move on the first empty cell
            x, y = empty_cells[0]
            print(f"Placing item at ({x}, {y})")
            result = self.make_move(x, y)
            if not result:
                print(f"Failed to make move at ({x}, {y})")
                # Try the next empty cell
                if len(empty_cells) > 1:
                    x, y = empty_cells[1]
                    print(f"Trying next empty cell at ({x}, {y})")
                    result = self.make_move(x, y)
                    if not result:
                        print(f"Failed to make move at ({x}, {y}) as well")
                        # If we can't make any moves, break
                        break
            
            moves_made += 1
            
            # Check if game over after each move
            if self.game_state["game_over"]:
                print(f"Game over detected after {moves_made} moves!")
                self.print_grid()
                self.assert_test(True, "Game Over Detection", 
                                "Game over flag correctly set to true when board is full")
                return True
        
        # If we reach here, we couldn't fill the board or game over wasn't detected
        print(f"Made {moves_made} moves but couldn't fill the board or game over wasn't detected")
        self.print_grid()
        
        # Count empty cells one more time
        empty_count = sum(row.count(-99) for row in self.game_state["grid"])
        
        if empty_count == 0 and not self.game_state["game_over"]:
            self.assert_test(False, "Game Over Detection", 
                            "Board is full but game_over flag is not set to true")
        else:
            self.assert_test(False, "Game Over Detection", 
                            f"Could not fill the board after {moves_made} moves. {empty_count} empty cells remain.")
        
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