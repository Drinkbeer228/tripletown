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

# Test class for Triple Town game backend
class TripleTownBackendTest:
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
    
    def test_create_new_game(self):
        """Test creating a new game"""
        print("\n=== Testing Game Creation ===")
        response = requests.post(f"{API_URL}/game/new")
        
        # Check response status
        self.assert_test(response.status_code == 200, "Create game returns 200 status code")
        
        # Parse response
        try:
            data = response.json()
            self.game_id = data.get("id")
            self.game_state = data
            
            # Verify game structure
            self.assert_test(self.game_id is not None, "Game ID is present")
            self.assert_test(isinstance(data.get("grid"), list), "Grid is a list")
            self.assert_test(len(data.get("grid", [])) == 6, "Grid has 6 rows")
            
            # Check all cells are empty (-99)
            all_empty = all(cell == -99 for row in data.get("grid", []) for cell in row)
            self.assert_test(all_empty, "All grid cells are empty (-99)")
            
            # Check initial values
            self.assert_test(data.get("score") == 0, "Initial score is 0")
            self.assert_test(data.get("moves") == 0, "Initial moves count is 0")
            self.assert_test(data.get("game_over") is False, "Game over is initially False")
            self.assert_test(data.get("next_item") == 0, "First next_item is grass (0)")
            
            print(f"Created game with ID: {self.game_id}")
            return True
        except Exception as e:
            self.assert_test(False, "Parse game creation response", f"Error: {str(e)}")
            return False
    
    def test_get_game_state(self):
        """Test retrieving game state"""
        print("\n=== Testing Get Game State ===")
        if not self.game_id:
            self.assert_test(False, "Get game state", "No game ID available")
            return False
        
        response = requests.get(f"{API_URL}/game/{self.game_id}")
        
        # Check response status
        self.assert_test(response.status_code == 200, "Get game returns 200 status code")
        
        # Parse response
        try:
            data = response.json()
            self.assert_test(data.get("id") == self.game_id, "Retrieved correct game by ID")
            
            # Update game state
            self.game_state = data
            return True
        except Exception as e:
            self.assert_test(False, "Parse get game response", f"Error: {str(e)}")
            return False
    
    def test_invalid_game_id(self):
        """Test retrieving a non-existent game"""
        print("\n=== Testing Invalid Game ID ===")
        invalid_id = "nonexistent-game-id"
        
        response = requests.get(f"{API_URL}/game/{invalid_id}")
        self.assert_test(response.status_code == 404, "Invalid game ID returns 404")
        
        return True
    
    def test_make_move(self, x, y):
        """Test making a move"""
        if not self.game_id:
            self.assert_test(False, "Make move", "No game ID available")
            return False
        
        move_data = {
            "game_id": self.game_id,
            "x": x,
            "y": y
        }
        
        response = requests.post(f"{API_URL}/game/move", json=move_data)
        
        # Check response status
        if not self.assert_test(response.status_code == 200, "Move returns 200 status code"):
            return False
        
        # Parse response
        try:
            data = response.json()
            self.assert_test(data.get("success") is True, "Move was successful")
            
            # Update game state
            self.game_state = data.get("game_state")
            return data
        except Exception as e:
            self.assert_test(False, "Parse move response", f"Error: {str(e)}")
            return False
    
    def test_invalid_move(self):
        """Test making invalid moves"""
        print("\n=== Testing Invalid Moves ===")
        if not self.game_id:
            self.assert_test(False, "Test invalid move", "No game ID available")
            return False
        
        # Test out of bounds move
        move_data = {
            "game_id": self.game_id,
            "x": 10,  # Out of bounds
            "y": 0
        }
        
        response = requests.post(f"{API_URL}/game/move", json=move_data)
        self.assert_test(response.status_code == 200, "Out of bounds move returns 200")
        data = response.json()
        self.assert_test(data.get("success") is False, "Out of bounds move fails correctly")
        
        # Make a valid move first
        self.test_make_move(0, 0)
        
        # Test move on non-empty tile
        move_data = {
            "game_id": self.game_id,
            "x": 0,  # Already filled
            "y": 0
        }
        
        response = requests.post(f"{API_URL}/game/move", json=move_data)
        self.assert_test(response.status_code == 200, "Move on filled tile returns 200")
        data = response.json()
        self.assert_test(data.get("success") is False, "Move on filled tile fails correctly")
        
        return True
    
    def test_basic_merge(self):
        """Test basic merge of 3 grass into 1 bush"""
        print("\n=== Testing Basic Merge (3 Grass → 1 Bush) ===")
        
        # Create a new game for this test
        self.test_create_new_game()
        
        # Place 3 grass in a row (0, 0), (0, 1), (0, 2)
        # First move - always grass
        move1 = self.test_make_move(0, 0)
        self.assert_test(self.game_state["grid"][0][0] == 0, "First item placed is grass")
        
        # Second move - always grass
        move2 = self.test_make_move(0, 1)
        self.assert_test(self.game_state["grid"][0][1] == 0, "Second item placed is grass")
        
        # Third move - always grass, should trigger merge
        move3 = self.test_make_move(0, 2)
        
        # Check if merge happened
        merged_positions = move3.get("merged_positions", [])
        self.assert_test(len(merged_positions) >= 3, "At least 3 positions were merged")
        
        # Check if a bush was created at the first position
        self.assert_test(self.game_state["grid"][0][0] == 1, "Grass merged into bush at first position")
        
        # Check if other positions are empty
        self.assert_test(self.game_state["grid"][0][1] == -99, "Second position is now empty")
        self.assert_test(self.game_state["grid"][0][2] == -99, "Third position is now empty")
        
        # Check score increased
        self.assert_test(self.game_state["score"] > 0, "Score increased after merge")
        
        return True
    
    def test_item_progression_chain(self):
        """Test the complete item progression chain"""
        print("\n=== Testing Item Progression Chain ===")
        
        # Create a new game for this test
        self.test_create_new_game()
        
        # Dictionary to track the highest item type we've created
        highest_item = -1
        
        # Function to place items in a pattern to create merges
        def place_items_for_merge(item_type, count=3):
            nonlocal highest_item
            
            # Place items in a row
            for i in range(count):
                # Find an empty spot
                empty_found = False
                for x in range(6):
                    for y in range(6):
                        if self.game_state["grid"][x][y] == -99:  # Empty
                            # Temporarily modify the grid to place our desired item
                            self.game_state["grid"][x][y] = item_type
                            empty_found = True
                            break
                    if empty_found:
                        break
            
            # Now make one more move to trigger merge processing
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -99:  # Empty
                        move_result = self.test_make_move(x, y)
                        # Check if we created a higher tier item
                        for row in self.game_state["grid"]:
                            for cell in row:
                                highest_item = max(highest_item, cell)
                        return True
            
            return False
        
        # Test progression: grass(0) → bush(1) → tree(2) → house(3) → mansion(4) → castle(5) → crystal(6) → monument(7)
        progression = [
            {"name": "grass to bush", "from_type": 0, "to_type": 1},
            {"name": "bush to tree", "from_type": 1, "to_type": 2},
            {"name": "tree to house", "from_type": 2, "to_type": 3},
            {"name": "house to mansion", "from_type": 3, "to_type": 4},
            {"name": "mansion to castle", "from_type": 4, "to_type": 5},
            {"name": "castle to crystal", "from_type": 5, "to_type": 6},
            {"name": "crystal to monument", "from_type": 6, "to_type": 7}
        ]
        
        # We'll use a simplified approach for testing - directly manipulate the game state
        # This is a test-only approach to verify the merge logic works
        for step in progression:
            print(f"Testing {step['name']} progression...")
            
            # Create a new game for each step to have a clean slate
            self.test_create_new_game()
            
            # Place 3 items of the "from" type in a row
            for i in range(3):
                x, y = i, 0  # Place in first row
                move_data = {
                    "game_id": self.game_id,
                    "x": x,
                    "y": y
                }
                
                # Make the move
                response = requests.post(f"{API_URL}/game/move", json=move_data)
                data = response.json()
                
                # If this is the last move, check for merge
                if i == 2:
                    # Check if the first position now has the "to" type
                    self.game_state = data.get("game_state")
                    
                    # Look for the upgraded item anywhere on the board
                    found_upgraded = False
                    for row in self.game_state["grid"]:
                        if step["to_type"] in row:
                            found_upgraded = True
                            break
                    
                    self.assert_test(found_upgraded, 
                                    f"{step['name']} progression works", 
                                    f"Expected to find item type {step['to_type']} after merge")
        
        return True
    
    def test_bear_mechanics(self):
        """Test bear spawning, movement, and trapping"""
        print("\n=== Testing Bear Mechanics ===")
        
        # Create a new game
        self.test_create_new_game()
        
        # Make 10+ moves to increase bear spawn chance
        print("Making initial moves to increase bear spawn chance...")
        for i in range(15):
            # Find an empty spot
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -99:  # Empty
                        self.test_make_move(x, y)
                        break
                else:
                    continue
                break
        
        # Check if any bears have spawned
        bears_found = False
        for row in self.game_state["grid"]:
            if -1 in row:  # Bear
                bears_found = True
                break
        
        self.assert_test(bears_found, "Bears spawn after multiple moves")
        
        if not bears_found:
            print("No bears found, skipping bear trapping test")
            return True
        
        # Find a bear to trap
        bear_x, bear_y = None, None
        for x in range(6):
            for y in range(6):
                if self.game_state["grid"][x][y] == -1:  # Bear
                    bear_x, bear_y = x, y
                    break
            if bear_x is not None:
                break
        
        if bear_x is None:
            print("Could not locate a bear, skipping trapping test")
            return True
        
        print(f"Found bear at position ({bear_x}, {bear_y}), attempting to trap it...")
        
        # Try to surround the bear with items
        # We'll make moves around the bear to trap it
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        trapped_bear = False
        
        for dx, dy in directions:
            nx, ny = bear_x + dx, bear_y + dy
            if 0 <= nx < 6 and 0 <= ny < 6 and self.game_state["grid"][nx][ny] == -99:
                self.test_make_move(nx, ny)
                
                # Check if bear turned into tombstone
                if self.game_state["grid"][bear_x][bear_y] == -2:  # Tombstone
                    trapped_bear = True
                    break
        
        self.assert_test(trapped_bear, "Bears turn into tombstones when trapped")
        
        return True
    
    def test_game_over(self):
        """Test game over detection by filling the board"""
        print("\n=== Testing Game Over Detection ===")
        
        # Create a new game
        self.test_create_new_game()
        
        # Fill the entire board
        print("Filling the board to trigger game over...")
        for x in range(6):
            for y in range(6):
                if self.game_state["grid"][x][y] == -99:  # Empty
                    self.test_make_move(x, y)
        
        # Check if game over is detected
        self.assert_test(self.game_state["game_over"] is True, "Game over detected when board is full")
        
        # Try to make another move
        move_data = {
            "game_id": self.game_id,
            "x": 0,
            "y": 0
        }
        
        response = requests.post(f"{API_URL}/game/move", json=move_data)
        data = response.json()
        self.assert_test(data.get("success") is False, "Moves rejected after game over")
        
        return True
    
    def test_scoring_system(self):
        """Test the scoring system"""
        print("\n=== Testing Scoring System ===")
        
        # Create a new game
        self.test_create_new_game()
        
        # Initial score should be 0
        self.assert_test(self.game_state["score"] == 0, "Initial score is 0")
        
        # Make a move (no merge)
        self.test_make_move(0, 0)
        self.assert_test(self.game_state["score"] == 0, "No score change without merges")
        
        # Create a merge (3 grass → 1 bush)
        # Place 2 more grass tiles adjacent to the first one
        self.test_make_move(0, 1)
        initial_score = self.game_state["score"]
        move_result = self.test_make_move(0, 2)
        
        # Score should increase after merge
        score_increase = self.game_state["score"] - initial_score
        self.assert_test(score_increase > 0, f"Score increased by {score_increase} after merge")
        
        # The score increase should be based on the item type and merge size
        # For 3 grass (type 0), base score is (0+1)*10 * 3 = 30
        expected_min_score = 30
        self.assert_test(score_increase >= expected_min_score, 
                        f"Score increase ({score_increase}) is at least the expected minimum ({expected_min_score})")
        
        return True
    
    def test_progressive_difficulty(self):
        """Test that bear spawn rate increases after move 10"""
        print("\n=== Testing Progressive Difficulty ===")
        
        # Create a new game
        self.test_create_new_game()
        
        # Make 20 moves and count bears
        bears_before_10 = 0
        bears_after_10 = 0
        
        print("Making 20 moves to test bear spawn rate...")
        for i in range(20):
            # Find an empty spot
            move_made = False
            for x in range(6):
                for y in range(6):
                    if self.game_state["grid"][x][y] == -99:  # Empty
                        self.test_make_move(x, y)
                        move_made = True
                        
                        # Count bears on the board
                        bear_count = sum(row.count(-1) for row in self.game_state["grid"])
                        
                        if i < 10:
                            bears_before_10 = max(bears_before_10, bear_count)
                        else:
                            bears_after_10 = max(bears_after_10, bear_count)
                        
                        break
                if move_made:
                    break
        
        print(f"Bears before move 10: {bears_before_10}")
        print(f"Bears after move 10: {bears_after_10}")
        
        # Bears should start spawning after move 10
        self.assert_test(bears_before_10 == 0, "No bears spawn before move 10")
        
        # This is a probabilistic test, so it might not always pass
        # But with 10 moves after the threshold, we should see at least one bear
        self.assert_test(bears_after_10 > 0, "Bears spawn after move 10")
        
        return True
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n===== TRIPLE TOWN BACKEND API TESTS =====")
        
        # Basic API tests
        self.test_create_new_game()
        self.test_get_game_state()
        self.test_invalid_game_id()
        self.test_invalid_move()
        
        # Game mechanics tests
        self.test_basic_merge()
        self.test_item_progression_chain()
        self.test_bear_mechanics()
        self.test_scoring_system()
        self.test_progressive_difficulty()
        self.test_game_over()
        
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
    tester = TripleTownBackendTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)