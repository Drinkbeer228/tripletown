from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import random
import copy

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Game Constants
GRID_SIZE = 6
ITEM_TYPES = {
    0: {"name": "grass", "emoji": "🌱", "color": "#4ade80"},
    1: {"name": "bush", "emoji": "🌿", "color": "#22c55e"},  
    2: {"name": "tree", "emoji": "🌳", "color": "#16a34a"},
    3: {"name": "house", "emoji": "🏠", "color": "#dc2626"},
    4: {"name": "mansion", "emoji": "🏛️", "color": "#7c2d12"},
    5: {"name": "castle", "emoji": "🏰", "color": "#7c3aed"},
    6: {"name": "crystal", "emoji": "💎", "color": "#06b6d4"},
    7: {"name": "monument", "emoji": "🗿", "color": "#fbbf24"},
    -1: {"name": "bear", "emoji": "🐻", "color": "#92400e"},
    -2: {"name": "tombstone", "emoji": "🪦", "color": "#6b7280"},
    -3: {"name": "rock", "emoji": "🪨", "color": "#374151"}
}

# Game Models
class GameTile(BaseModel):
    item_type: int = -99  # -99 = empty, 0-7 = items, -1 = bear, -2 = tombstone, -3 = rock
    x: int
    y: int

class GameState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    grid: List[List[int]] = Field(default_factory=lambda: [[-99 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)])
    score: int = 0
    moves: int = 0
    next_item: int = 0
    game_over: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MoveRequest(BaseModel):
    game_id: str
    x: int
    y: int

class MoveResponse(BaseModel):
    success: bool
    game_state: GameState
    message: str = ""
    merged_positions: List[Dict[str, int]] = []

def generate_next_item(moves: int) -> int:
    """Generate next item based on game progression"""
    if moves < 5:
        return 0  # Only grass for first 5 moves
    elif moves < 15:
        # Mostly grass, some bush
        return random.choices([0, 1], weights=[80, 20])[0]
    elif moves < 30:
        # Grass, bush, rare tree
        return random.choices([0, 1, 2], weights=[60, 35, 5])[0]
    else:
        # More variety as game progresses
        return random.choices([0, 1, 2], weights=[50, 40, 10])[0]

def should_spawn_bear(moves: int) -> bool:
    """Determine if bear should spawn based on moves"""
    if moves < 10:
        return False
    bear_chance = min(15 + (moves // 10) * 5, 40)  # Increases every 10 moves, caps at 40%
    return random.randint(1, 100) <= bear_chance

def find_merge_groups(grid: List[List[int]], item_type: int) -> List[List[Dict[str, int]]]:
    """Find all groups of 3+ connected identical items"""
    visited = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    groups = []
    
    def dfs(x: int, y: int, group: List[Dict[str, int]]):
        if (x < 0 or x >= GRID_SIZE or y < 0 or 
            y >= GRID_SIZE or visited[x][y] or 
            grid[x][y] != item_type):
            return
        
        visited[x][y] = True
        group.append({"x": x, "y": y})
        
        # Check 4 directions
        dfs(x + 1, y, group)
        dfs(x - 1, y, group)
        dfs(x, y + 1, group)
        dfs(x, y - 1, group)
    
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if not visited[x][y] and grid[x][y] == item_type and item_type >= 0:
                group = []
                dfs(x, y, group)
                if len(group) >= 3:
                    groups.append(group)
    
    return groups

def process_merges(grid: List[List[int]]) -> tuple[List[List[int]], int, List[Dict[str, int]]]:
    """Process all possible merges and return updated grid, score gained, and merged positions"""
    score_gained = 0
    all_merged_positions = []
    
    # Keep merging until no more merges possible
    while True:
        merged_this_round = False
        
        # Check each item type for merges (0-7, -2 for tombstones)
        for item_type in list(range(8)) + [-2]:
            groups = find_merge_groups(grid, item_type)
            
            for group in groups:
                if len(group) >= 3:
                    merged_this_round = True
                    
                    # Calculate score based on item type and group size
                    base_score = (item_type + 1) * 10 if item_type >= 0 else 5
                    score_gained += base_score * len(group)
                    
                    # Add to merged positions
                    all_merged_positions.extend(group)
                    
                    # Clear merged tiles
                    for pos in group:
                        grid[pos["x"]][pos["y"]] = -99
                    
                    # Place upgraded item at first position (if not max level)
                    first_pos = group[0]
                    if item_type < 6:  # Can upgrade up to crystal
                        grid[first_pos["x"]][first_pos["y"]] = item_type + 1
                    elif item_type == 6:  # 3 crystals make monument
                        grid[first_pos["x"]][first_pos["y"]] = 7
                    # Tombstones (-2) merge into grass (0)
                    elif item_type == -2:
                        grid[first_pos["x"]][first_pos["y"]] = 0
        
        if not merged_this_round:
            break
    
    return grid, score_gained, all_merged_positions

def move_bears(grid: List[List[int]]) -> List[List[int]]:
    """Move bears randomly and trap them if surrounded"""
    bear_positions = []
    
    # Find all bears
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if grid[x][y] == -1:  # Bear
                bear_positions.append((x, y))
    
    # Move each bear
    for bear_x, bear_y in bear_positions:
        # Check if bear is trapped (surrounded by non-empty tiles)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        empty_neighbors = []
        
        for dx, dy in directions:
            nx, ny = bear_x + dx, bear_y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                if grid[nx][ny] == -99:  # Empty tile
                    empty_neighbors.append((nx, ny))
        
        if not empty_neighbors:
            # Bear is trapped, turn into tombstone
            grid[bear_x][bear_y] = -2
        else:
            # Move bear to random empty neighbor
            new_x, new_y = random.choice(empty_neighbors)
            grid[bear_x][bear_y] = -99  # Clear old position
            grid[new_x][new_y] = -1     # Place bear at new position
    
    return grid

def is_game_over(grid: List[List[int]]) -> bool:
    """Check if game is over (no empty tiles)"""
    for row in grid:
        for cell in row:
            if cell == -99:
                return False
    return True

# API Routes
@api_router.post("/game/new", response_model=GameState)
async def create_new_game():
    """Create a new game"""
    game_state = GameState()
    game_state.next_item = generate_next_item(0)
    
    # Save to database
    await db.games.insert_one(game_state.dict())
    
    return game_state

@api_router.get("/game/{game_id}", response_model=GameState)
async def get_game(game_id: str):
    """Get current game state"""
    game_doc = await db.games.find_one({"id": game_id})
    if not game_doc:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return GameState(**game_doc)

@api_router.post("/game/move", response_model=MoveResponse)
async def make_move(move_request: MoveRequest):
    """Make a move in the game"""
    # Get current game state
    game_doc = await db.games.find_one({"id": move_request.game_id})
    if not game_doc:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_state = GameState(**game_doc)
    
    if game_state.game_over:
        return MoveResponse(success=False, game_state=game_state, message="Game is over")
    
    x, y = move_request.x, move_request.y
    
    # Validate move
    if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
        return MoveResponse(success=False, game_state=game_state, message="Invalid position")
    
    if game_state.grid[x][y] != -99:  # Not empty
        return MoveResponse(success=False, game_state=game_state, message="Tile is not empty")
    
    # Place item
    current_item = game_state.next_item
    if should_spawn_bear(game_state.moves) and current_item >= 0:
        # Sometimes spawn bear instead of regular item
        game_state.grid[x][y] = -1  # Bear
    else:
        game_state.grid[x][y] = current_item
    
    game_state.moves += 1
    
    # Process merges
    game_state.grid, score_gained, merged_positions = process_merges(game_state.grid)
    game_state.score += score_gained
    
    # Move bears
    game_state.grid = move_bears(game_state.grid)
    
    # Generate next item
    game_state.next_item = generate_next_item(game_state.moves)
    
    # Check game over
    game_state.game_over = is_game_over(game_state.grid)
    
    # Update database
    await db.games.replace_one(
        {"id": move_request.game_id}, 
        game_state.dict()
    )
    
    return MoveResponse(
        success=True, 
        game_state=game_state, 
        message="Move successful",
        merged_positions=merged_positions
    )

@api_router.get("/game/{game_id}/high-scores")
async def get_high_scores():
    """Get high scores"""
    games = await db.games.find(
        {"game_over": True}, 
        {"score": 1, "moves": 1, "created_at": 1}
    ).sort("score", -1).limit(10).to_list(10)
    
    return games

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()