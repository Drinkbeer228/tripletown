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
    0: {"name": "bottle", "emoji": "🍾", "color": "#f59e0b"},  # Grass -> Bottle
    1: {"name": "pint", "emoji": "🥛", "color": "#fbbf24"},    # Bush -> Pint
    2: {"name": "keg", "emoji": "🛢️", "color": "#eab308"},   # Tree -> Keg
    3: {"name": "pub", "emoji": "🍻", "color": "#ca8a04"},    # House -> Pub
    4: {"name": "brewery", "emoji": "🏭", "color": "#a16207"},# Mansion -> Brewery
    5: {"name": "factory", "emoji": "🏭", "color": "#854d0e"},# Castle -> Factory
    6: {"name": "empire", "emoji": "🌆", "color": "#713f12"}, # Crystal -> Empire
    7: {"name": "monument", "emoji": "🗽", "color": "#4d2c0e"},# Monument
    -1: {"name": "thief", "emoji": "🕵️", "color": "#92400e"},# Bear -> Thief
    -2: {"name": "trap", "emoji": "🪤", "color": "#6b7280"},  # Tombstone -> Trap
    -3: {"name": "obstacle", "emoji": "🚧", "color": "#374151"}# Rock -> Obstacle
}

# Game Models (unchanged)
class GameTile(BaseModel):
    item_type: int = -99
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
    if moves < 5:
        return 0
    elif moves < 15:
        return random.choices([0, 1], weights=[80, 20])[0]
    elif moves < 30:
        return random.choices([0, 1, 2], weights=[60, 35, 5])[0]
    else:
        return random.choices([0, 1, 2], weights=[50, 40, 10])[0]

def should_spawn_thief(moves: int) -> bool:  # Renamed from bear
    if moves < 10:
        return False
    thief_chance = min(15 + (moves // 10) * 5, 40)
    return random.randint(1, 100) <= thief_chance

def find_merge_groups(grid: List[List[int]], item_type: int) -> List[List[Dict[str, int]]]:
    visited = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    groups = []
    
    def dfs(x: int, y: int, group: List[Dict[str, int]]):
        if (x < 0 or x >= GRID_SIZE or y < 0 or y >= GRID_SIZE or visited[x][y] or grid[x][y] != item_type):
            return
        visited[x][y] = True
        group.append({"x": x, "y": y})
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
    score_gained = 0
    all_merged_positions = []
    
    while True:
        merged_this_round = False
        
        for item_type in list(range(8)) + [-2]:  # Items 0-7 and traps (-2)
            groups = find_merge_groups(grid, item_type)
            
            for group in groups:
                if len(group) >= 3:
                    merged_this_round = True
                    
                    base_score = (item_type + 1) * 10 if item_type >= 0 else 5
                    bonus = 1.5 if len(group) > 3 else 1  # Bonus for big combos
                    score_gained += int(base_score * len(group) * bonus)
                    
                    all_merged_positions.extend(group)
                    
                    for pos in group:
                        grid[pos["x"]][pos["y"]] = -99
                    
                    first_pos = group[0]
                    if item_type < 6:
                        grid[first_pos["x"]][first_pos["y"]] = item_type + 1
                    elif item_type == 6:
                        grid[first_pos["x"]][first_pos["y"]] = 7
                    elif item_type == -2:  # Traps merge to bottle (0)
                        grid[first_pos["x"]][first_pos["y"]] = 0
        
        if not merged_this_round:
            break
    
    return grid, score_gained, all_merged_positions

def is_thief_trapped(grid: List[List[int]], thief_x: int, thief_y: int) -> bool:  # Simplified: no empty neighbors
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    for dx, dy in directions:
        nx, ny = thief_x + dx, thief_y + dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and grid[nx][ny] == -99:
            return False  # Has empty neighbor -> not trapped
    return True  # All neighbors occupied -> trapped

def move_thieves(grid: List[List[int]]) -> List[List[int]]:  # Renamed from bears
    thief_positions = []
    
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if grid[x][y] == -1:
                thief_positions.append((x, y))
    
    for thief_x, thief_y in thief_positions:
        if is_thief_trapped(grid, thief_x, thief_y):
            grid[thief_x][thief_y] = -2  # Trap
        else:
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            empty_neighbors = []
            for dx, dy in directions:
                nx, ny = thief_x + dx, thief_y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and grid[nx][ny] == -99:
                    empty_neighbors.append((nx, ny))
            if empty_neighbors:
                new_x, new_y = random.choice(empty_neighbors)
                grid[thief_x][thief_y] = -99
                grid[new_x][new_y] = -1
    
    return grid

def is_game_over(grid: List[List[int]]) -> bool:
    for row in grid:
        for cell in row:
            if cell == -99:
                return False
    return True

# API Routes (unchanged, but updated names like thief)
@api_router.post("/game/new", response_model=GameState)
async def create_new_game():
    game_state = GameState()
    game_state.next_item = generate_next_item(0)
    await db.games.insert_one(game_state.dict())
    return game_state

@api_router.get("/game/{game_id}", response_model=GameState)
async def get_game(game_id: str):
    game_doc = await db.games.find_one({"id": game_id})
    if not game_doc:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameState(**game_doc)

@api_router.post("/game/move", response_model=MoveResponse)
async def make_move(move_request: MoveRequest):
    game_doc = await db.games.find_one({"id": move_request.game_id})
    if not game_doc:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game_state = GameState(**game_doc)
    
    if game_state.game_over:
        return MoveResponse(success=False, game_state=game_state, message="Game is over")
    
    x, y = move_request.x, move_request.y
    
    if not (0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE):
        return MoveResponse(success=False, game_state=game_state, message="Invalid position")
    
    if game_state.grid[x][y] != -99:
        return MoveResponse(success=False, game_state=game_state, message="Tile is not empty")
    
    current_item = game_state.next_item
    if should_spawn_thief(game_state.moves) and current_item >= 0:
        game_state.grid[x][y] = -1  # Thief
    else:
        game_state.grid[x][y] = current_item
    
    game_state.moves += 1
    
    game_state.grid, score_gained, merged_positions = process_merges(game_state.grid)
    game_state.score += score_gained
    
    game_state.grid = move_thieves(game_state.grid)
    
    game_state.next_item = generate_next_item(game_state.moves)
    
    game_state.game_over = is_game_over(game_state.grid)
    
    await db.games.replace_one({"id": move_request.game_id}, game_state.dict())
    
    return MoveResponse(
        success=True, 
        game_state=game_state, 
        message="Move successful",
        merged_positions=merged_positions
    )

@api_router.get("/game/{game_id}/high-scores")
async def get_high_scores():
    games = await db.games.find({"game_over": True}, {"score": 1, "moves": 1, "created_at": 1}).sort("score", -1).limit(10).to_list(10)
    return games

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
