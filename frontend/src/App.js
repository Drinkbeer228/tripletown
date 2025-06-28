import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const GRID_SIZE = 6;
const ITEM_TYPES = {
  0: { name: "grass", emoji: "🌱", color: "#4ade80" },
  1: { name: "bush", emoji: "🌿", color: "#22c55e" },
  2: { name: "tree", emoji: "🌳", color: "#16a34a" },
  3: { name: "house", emoji: "🏠", color: "#dc2626" },
  4: { name: "mansion", emoji: "🏛️", color: "#7c2d12" },
  5: { name: "castle", emoji: "🏰", color: "#7c3aed" },
  6: { name: "crystal", emoji: "💎", color: "#06b6d4" },
  7: { name: "monument", emoji: "🗿", color: "#fbbf24" },
  [-1]: { name: "bear", emoji: "🐻", color: "#92400e" },
  [-2]: { name: "tombstone", emoji: "🪦", color: "#6b7280" },
  [-3]: { name: "rock", emoji: "🪨", color: "#374151" },
  [-99]: { name: "empty", emoji: "", color: "#1f2937" }
};

function App() {
  const [gameState, setGameState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [animatingTiles, setAnimatingTiles] = useState(new Set());

  const createNewGame = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/game/new`);
      setGameState(response.data);
      setMessage("New game started! Place items to build your town.");
    } catch (error) {
      console.error('Error creating game:', error);
      setMessage("Error creating game. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const makeMove = async (x, y) => {
    if (!gameState || gameState.game_over || loading) return;
    
    setLoading(true);
    try {
      const response = await axios.post(`${API}/game/move`, {
        game_id: gameState.id,
        x: x,
        y: y
      });
      
      if (response.data.success) {
        setGameState(response.data.game_state);
        
        // Animate merged tiles
        if (response.data.merged_positions.length > 0) {
          const mergedSet = new Set(
            response.data.merged_positions.map(pos => `${pos.x}-${pos.y}`)
          );
          setAnimatingTiles(mergedSet);
          setTimeout(() => setAnimatingTiles(new Set()), 600);
          setMessage(`Merged ${response.data.merged_positions.length} tiles! +${response.data.merged_positions.length * 10} points`);
        } else {
          setMessage("Item placed!");
        }
        
        if (response.data.game_state.game_over) {
          setMessage(`Game Over! Final Score: ${response.data.game_state.score}`);
        }
      } else {
        setMessage(response.data.message);
      }
    } catch (error) {
      console.error('Error making move:', error);
      setMessage("Error making move. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getTileContent = (itemType) => {
    const item = ITEM_TYPES[itemType];
    if (!item) return { emoji: "", color: "#1f2937" };
    return item;
  };

  const getTileKey = (x, y) => `${x}-${y}`;

  useEffect(() => {
    createNewGame();
  }, []);

  if (!gameState) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-emerald-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading Triple Town...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 via-green-800 to-emerald-900 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-4xl font-bold text-white mb-2 font-serif">
            🏘️ Triple Town
          </h1>
          <p className="text-green-200 text-lg">
            Match 3 items to build your town!
          </p>
        </div>

        {/* Game Stats */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-white">{gameState.score}</div>
              <div className="text-green-200 text-sm">Score</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-white">{gameState.moves}</div>
              <div className="text-green-200 text-sm">Moves</div>
            </div>
            <div>
              <div className="text-4xl">{getTileContent(gameState.next_item).emoji}</div>
              <div className="text-green-200 text-sm">Next Item</div>
            </div>
            <div>
              <button
                onClick={createNewGame}
                disabled={loading}
                className="bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-white px-4 py-2 rounded-lg transition-colors font-semibold"
              >
                New Game
              </button>
            </div>
          </div>
        </div>

        {/* Message */}
        {message && (
          <div className="bg-blue-500/20 border border-blue-400/30 text-blue-100 px-4 py-2 rounded-lg mb-4 text-center">
            {message}
          </div>
        )}

        {/* Game Over Overlay */}
        {gameState.game_over && (
          <div className="bg-red-500/20 border border-red-400/30 text-red-100 px-6 py-4 rounded-lg mb-4 text-center">
            <h2 className="text-2xl font-bold mb-2">🎮 Game Over!</h2>
            <p className="text-lg">Final Score: <span className="font-bold">{gameState.score}</span></p>
            <p className="text-sm mt-2">No more empty spaces left. Start a new game!</p>
          </div>
        )}

        {/* Game Grid */}
        <div className="flex justify-center mb-6">
          <div className="grid grid-cols-6 gap-2 p-4 bg-white/10 backdrop-blur-sm rounded-xl border-2 border-white/20">
            {gameState.grid.map((row, x) =>
              row.map((cell, y) => {
                const tileKey = getTileKey(x, y);
                const isAnimating = animatingTiles.has(tileKey);
                const tileContent = getTileContent(cell);
                const isEmpty = cell === -99;
                
                return (
                  <button
                    key={tileKey}
                    onClick={() => makeMove(x, y)}
                    disabled={!isEmpty || gameState.game_over || loading}
                    className={`
                      w-16 h-16 md:w-20 md:h-20 rounded-lg border-2 transition-all duration-200
                      flex items-center justify-center text-2xl md:text-3xl font-bold relative
                      ${isEmpty 
                        ? 'bg-gray-800/50 border-gray-600 hover:bg-gray-700/50 hover:border-gray-500 cursor-pointer hover:scale-105' 
                        : 'border-white/30 cursor-default'
                      }
                      ${isAnimating ? 'animate-bounce bg-yellow-400/30 border-yellow-400' : ''}
                      ${gameState.game_over ? 'opacity-75' : ''}
                    `}
                    style={{
                      backgroundColor: isEmpty ? undefined : `${tileContent.color}20`,
                      borderColor: isEmpty ? undefined : `${tileContent.color}60`
                    }}
                  >
                    {tileContent.emoji}
                    {isAnimating && (
                      <div className="absolute inset-0 bg-yellow-400/20 rounded-lg animate-pulse"></div>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
          <h3 className="text-white font-bold mb-3 text-center">Item Progression</h3>
          <div className="grid grid-cols-4 md:grid-cols-8 gap-2 text-center">
            {Object.entries(ITEM_TYPES).map(([key, item]) => {
              const itemKey = parseInt(key);
              if (itemKey < 0 || itemKey > 7) return null;
              
              return (
                <div key={key} className="flex flex-col items-center">
                  <div className="text-2xl mb-1">{item.emoji}</div>
                  <div className="text-white text-xs font-medium capitalize">
                    {item.name}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 text-center text-green-200 text-sm">
            <p className="mb-1">🐻 Bears block tiles until trapped by surrounding them</p>
            <p>🪦 Trapped bears become tombstones that can merge into grass</p>
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-6 bg-white/10 backdrop-blur-sm rounded-lg p-4 text-center">
          <h3 className="text-white font-bold mb-2">How to Play</h3>
          <div className="text-green-200 text-sm space-y-1">
            <p>• Click empty tiles to place items</p>
            <p>• Match 3+ identical adjacent items to merge them</p>
            <p>• Build from grass all the way up to monuments</p>
            <p>• Trap bears by surrounding them</p>
            <p>• Game ends when the board fills up</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;