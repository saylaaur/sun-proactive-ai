import os
from fastapi import FastAPI
from supabase import create_client, Client
from dotenv import load_dotenv

from semantic_matcher import get_embedding 
from ai_service import process_curator_input

load_dotenv("api_key.env")

app = FastAPI()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/")
def check():
    return {"message": "Бэкенд готов к работе!"}

@app.post("/register")
async def register(name: str, bio: str):
    full_vector = get_embedding(bio)
    vector = full_vector[:768]
    data = {"name": name, "bio": bio, "embedding": vector}
    return supabase.table("volunteers").insert(data).execute()

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
    
    
@app.post("/assign_task")
async def assign_task(volunteer_id: int, task_name: str):
    
    notification_text = f"Привет! Для тебя есть новая задача: {task_name}"
    
    
    return {
        "status": "success",
        "message": f"Уведомление для волонтера #{volunteer_id} сформировано",
        "preview": notification_text
    }


@app.post("/complete_task")
async def complete_task(volunteer_id: str, hours_spent: int):

    user = supabase.table("volunteers").select("hours").eq("id", volunteer_id).single().execute()
    new_hours = (user.data.get("hours") or 0) + hours_spent
    
   
    supabase.table("volunteers").update({"hours": new_hours}).eq("id", volunteer_id).execute()
    
    return {"status": "success", "total_hours": new_hours}



@app.post("/tasks")
async def create_task(title: str, description: str):
    return supabase.table("tasks").insert({"title": title, "description": description}).execute()

@app.get("/tasks")
async def get_tasks():
    return supabase.table("tasks").select("*").execute()


@app.post("/responses")
async def apply_to_task(task_id: str, volunteer_id: str):
    return supabase.table("responses").insert({"task_id": task_id, "volunteer_id": volunteer_id}).execute()


@app.get("/notifications")
async def get_notifications():
   
    return {
        "show_banner": True, 
        "message": "Внимание! Появилась новая задача: Нужна помощь в приюте!"
    }