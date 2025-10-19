const gridSize = 6;
const gameContainer = document.getElementById("game");
let grid = Array.from({ length: gridSize }, () => Array(gridSize).fill(0));

function createGrid() {
  gameContainer.innerHTML = "";
  for (let y = 0; y < gridSize; y++) {
    for (let x = 0; x < gridSize; x++) {
      const cell = document.createElement("div");
      cell.classList.add("cell");
      const value = grid[y][x];
      if (value > 0) {
        cell.dataset.type = value;
        cell.textContent = value;
      }
      cell.addEventListener("click", () => handleClick(x, y));
      gameContainer.appendChild(cell);
    }
  }
}

function getRandomTile() {
  return Math.random() < 0.8 ? 1 : 2; // 1 — трава, 2 — куст
}

function handleClick(x, y) {
  if (grid[y][x] !== 0) return;

  grid[y][x] = getRandomTile();
  mergeTiles();
  createGrid();
}

function mergeTiles() {
  let merged = false;
  for (let y = 0; y < gridSize; y++) {
    for (let x = 0; x < gridSize; x++) {
      const val = grid[y][x];
      if (val === 0) continue;

      const sameTiles = [[x, y]];

      [[1,0], [-1,0], [0,1], [0,-1]].forEach(([dx, dy]) => {
        if (grid[y+dy] && grid[y+dy][x+dx] === val)
          sameTiles.push([x+dx, y+dy]);
      });

      if (sameTiles.length >= 3) {
        sameTiles.forEach(([xx, yy]) => grid[yy][xx] = 0);
        grid[y][x] = val + 1;
        merged = true;
      }
    }
  }

  if (merged) mergeTiles(); // повторно ищем, если новые комбо появились
}

createGrid();
