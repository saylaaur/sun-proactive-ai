import os
import json
import numpy as np
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai

# 1. Загрузка ключа
load_dotenv("api_key.env")

# 1. СХЕМЫ ДАННЫХ (Data Contracts)
class Volunteer(BaseModel):
    id: str
    name: str
    bio: str
    skills: List[str]
    embedding: Optional[List[float]] = None

class UrgentTask(BaseModel):
    id: str
    title: str
    description: str

class PushNotification(BaseModel):
    volunteer_id: str
    task_id: str
    match_score: float
    push_text: str

# 2. ИНИЦИАЛИЗАЦИЯ API И МОДЕЛЕЙ
def init_api():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            from google.colab import userdata
            api_key = userdata.get('GEMINI_API_KEY')
        except:
            pass
            
    if not api_key:
        raise ValueError("Критическая ошибка: GEMINI_API_KEY не найден")
    genai.configure(api_key=api_key)

def get_embedding(text: str) -> List[float]:
    """Генерирует вектор для текста (используется для задач и волонтеров)"""
    init_api()
    available_models = [m.name for m in genai.list_models() if 'embedContent' in m.supported_generation_methods]
    model_name = available_models[0] 
    
    result = genai.embed_content(
        model=model_name,
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def calculate_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Математический расчет косинусного сходства"""
    v1, v2 = np.array(vec1), np.array(vec2)
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0.0
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


# 3. ГЕНЕРАЦИЯ PUSH-УВЕДОМЛЕНИЙ

def generate_push_text(volunteer: Volunteer, task: UrgentTask) -> str:
    """LLM генерирует короткий текст пуша на основе навыков юзера"""
    init_api()
    
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in all_models if 'flash' in m]
        model_name = flash_models[0] if flash_models else all_models[0]
    except:
        model_name = 'gemini-1.5-flash'
        
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    Ты — AI-менеджер платформы Sun Proactive. 
    До старта задачи "{task.title}" осталось менее 24 часов, нам не хватает людей!
    
    Волонтер: {volunteer.name}
    Его профиль: {volunteer.bio}, навыки: {', '.join(volunteer.skills)}
    
    Напиши ОДНО короткое Push-уведомление (до 120 символов) для этого человека.
    Сделай акцент на том, что именно ЕГО навыки спасут ситуацию. Используй призыв к действию.
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

# 4. ГЛАВНЫЙ ФОНОВЫЙ ПРОЦЕСС (CRON JOB LOGIC)
def process_urgent_tasks(urgent_tasks: List[UrgentTask], available_volunteers: List[Volunteer], top_n: int = 3) -> List[dict]:
    """
    Бэкенд передает сюда список горящих задач и свободных волонтеров.
    Система возвращает готовый план рассылки уведомлений.
    """
    print(f"🚀 AI Manager запущен. Обработка {len(urgent_tasks)} горящих задач...")
    notifications_plan = []

    for task in urgent_tasks:
        task_text = f"{task.title}. {task.description}"
        task_vector = get_embedding(task_text)
        
        # Считаем совпадения для всех волонтеров
        scored_volunteers = []
        for vol in available_volunteers:
            if not vol.embedding:
                vol_text = f"{vol.bio} Опыт: {' '.join(vol.skills)}"
                vol.embedding = get_embedding(vol_text)
                
            score = calculate_similarity(task_vector, vol.embedding)
            scored_volunteers.append({"volunteer": vol, "score": score})
            
        # Сортируем и берем лучших
        scored_volunteers.sort(key=lambda x: x['score'], reverse=True)
        top_matches = scored_volunteers[:top_n]
        
        # Генерируем пуши для победителей
        for match in top_matches:
            vol = match["volunteer"]
            push_text = generate_push_text(vol, task)
            
            notifications_plan.append({
                "task_id": task.id,
                "volunteer_id": vol.id,
                "volunteer_name": vol.name,
                "match_score_percent": round(match["score"] * 100, 1),
                "push_message": push_text
            })
            
    return notifications_plan

#test

if __name__ == "__main__":
    print(f"{'='*20} ТЕСТ АВТОНОМНОГО МЕНЕДЖЕРА {'='*20}\n")
    
    test_tasks = [
        UrgentTask(id="task_001", title="Эко-патруль на реке", description="Срочно нужна помощь в координации людей и выдаче инвентаря на берегу.")
    ]
    
    test_volunteers = [
        Volunteer(id="vol_1", name="Марина", bio="Организатор мероприятий, могу управлять толпой.", skills=["Координация", "Лидерство"]),
        Volunteer(id="vol_2", name="Игорь", bio="Программист, сижу дома, пишу код.", skills=["Python", "Базы данных"])
    ]
    
    print("⏳ AI ищет спасателей и пишет им сообщения...\n")
    plan = process_urgent_tasks(test_tasks, test_volunteers, top_n=1)
    
    print("📲 ПЛАН РАССЫЛКИ (готово к отправке):")
    print(json.dumps(plan, indent=2, ensure_ascii=False))