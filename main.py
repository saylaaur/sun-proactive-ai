import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
from dotenv import load_dotenv

# Импорт ваших модулей
from semantic_matcher import get_embedding 
from ai_service import process_curator_input

load_dotenv("api_key.env")

app = FastAPI()

# Настройка Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 1. ГЛАВНАЯ СТРАНИЦА (отдает ваш index.html)
@app.get("/")
async def read_index():
    # Отправляет файл index.html, который лежит в той же папке, что и main.py
    return FileResponse('index.html')

# 2. РЕГИСТРАЦИЯ
@app.post("/register")
async def register(name: str, bio: str):
    full_vector = get_embedding(bio)
    vector = full_vector[:768]
    data = {"name": name, "bio": bio, "embedding": vector}
    return supabase.table("volunteers").insert(data).execute()

# 3. ПОДБОР ВОЛОНТЕРОВ
@app.post("/match_volunteers")
async def match(task_description: str):
    full_vector = get_embedding(task_description)
    task_vector = full_vector[:768]
    
    rpc_data = {
        "query_embedding": task_vector, 
        "match_threshold": 0.5, 
        "match_count": 5
    }
    
    try:
        response = supabase.rpc("match_volunteers", rpc_data).execute()
        return {"best_matches": response.data}
    except Exception as e:
        return {"error": str(e)}

# 4. НАЗНАЧЕНИЕ ЗАДАЧИ
@app.post("/assign_task")
async def assign_task(volunteer_id: int, task_name: str):
    notification_text = f"Привет! Для тебя есть новая задача: {task_name}"
    return {
        "status": "success",
        "message": f"Уведомление для волонтера #{volunteer_id} сформировано",
        "preview": notification_text
    }

# 5. ЗАВЕРШЕНИЕ ЗАДАЧИ
@app.post("/complete_task")
async def complete_task(volunteer_id: str, hours_spent: int):
    user = supabase.table("volunteers").select("hours").eq("id", volunteer_id).single().execute()
    new_hours = (user.data.get("hours") or 0) + hours_spent
    supabase.table("volunteers").update({"hours": new_hours}).eq("id", volunteer_id).execute()
    return {"status": "success", "total_hours": new_hours}

# 6. УПРАВЛЕНИЕ ЗАДАЧАМИ
@app.post("/tasks")
async def create_task(title: str, description: str):
    return supabase.table("tasks").insert({"title": title, "description": description}).execute()

@app.get("/tasks")
async def get_tasks():
    return supabase.table("tasks").select("*").execute()

# 7. ОТКЛИКИ
@app.post("/responses")
async def apply_to_task(task_id: str, volunteer_id: str):
    return supabase.table("responses").insert({"task_id": task_id, "volunteer_id": volunteer_id}).execute()

# 8. УВЕДОМЛЕНИЯ
@app.get("/notifications")
async def get_notifications():
    return {
        "show_banner": True, 
        "message": "Внимание! Появилась новая задача: Нужна помощь в приюте!"
    }

# 9. ПОДКЛЮЧЕНИЕ СТАТИКИ (Чтобы работали JS и CSS файлы в той же папке)
# ВАЖНО: Эта строка должна быть в самом конце!
app.mount("/", StaticFiles(directory=".", html=True), name="static")
