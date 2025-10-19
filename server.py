from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json, os

app = FastAPI()

# Подключаем фронтенд
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# Файл для хранения рекордов
SCORE_FILE = "data/scores.json"

def load_scores():
    if not os.path.exists(SCORE_FILE):
        return []
    with open(SCORE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_scores(scores):
    os.makedirs(os.path.dirname(SCORE_FILE), exist_ok=True)
    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

@app.post("/api/score")
async def save_score(request: Request):
    data = await request.json()
    name = data.get("name", "Игрок")
    score = data.get("score", 0)
    scores = load_scores()
    scores.append({"name": name, "score": score})
    save_scores(scores)
    return JSONResponse({"status": "ok"})

@app.get("/api/scores")
def get_scores():
    scores = sorted(load_scores(), key=lambda x: x["score"], reverse=True)
    return JSONResponse(scores[:10])
