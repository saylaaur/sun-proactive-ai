import os
import json
import numpy as np
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import google.generativeai as genai


load_dotenv("api_key.env")

# DATA CONTRACTS (Схемы данных)
class Volunteer(BaseModel):
    id: str
    name: str
    bio: str
    skills: List[str]
    # Вектор будет храниться здесь (список чисел)
    embedding: List[float] = Field(default_factory=list)


# CORE LOGIC 
def init_api():
    """Умная инициализация API (работает локально у бэкендера и в Colab)"""
    api_key = None
    
    
    try:
        from google.colab import userdata
        api_key = userdata.get('GEMINI_API_KEY')
    except (ImportError, Exception):
        pass
        
    
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        
    if not api_key:
        raise ValueError("Критическая ошибка: GEMINI_API_KEY не найден в файле api_key.env")
        
    genai.configure(api_key=api_key)

def get_embedding(text: str) -> List[float]:
    """Динамически находит доступную модель и превращает текст в вектор"""
    init_api()
    
   
    available_models = [m.name for m in genai.list_models() if 'embedContent' in m.supported_generation_methods]
    if not available_models:
        raise ValueError("Ошибка доступа: Твой API-ключ не имеет доступа к моделям эмбеддингов.")
        
    model_name = available_models[0] # Берем первую 100% рабочую
    
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

def generate_explainable_reasoning(task_text: str, volunteer: Volunteer) -> str:
    """Explainable AI: объясняет, почему выбран именно этот человек"""
    init_api()
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Ты — AI-координатор фонда. 
    Напиши ОДНО короткое предложение, объясняющее куратору, почему этот волонтер идеально подходит для задачи.
    Начинай фразу со слов: "Рекомендуем этого кандидата: ..."
    
    Задача: {task_text}
    Волонтер: {volunteer.name}
    Опыт: {volunteer.bio}
    Навыки: {', '.join(volunteer.skills)}
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()


# MAIN SERVICE (Точка входа для Бэкенда)

def find_best_volunteers(task_text: str, volunteers: List[Volunteer], top_n: int = 2) -> List[dict]:
    """
    Основная функция: принимает текст задачи и список юзеров из БД, 
    возвращает Топ-N с аргументацией.
    """
    task_vector = get_embedding(task_text)
    
    results = []
    for vol in volunteers:
        
        if not vol.embedding:
            vol_text = f"{vol.bio} Опыт: {' '.join(vol.skills)}"
            vol.embedding = get_embedding(vol_text)
            
        score = calculate_similarity(task_vector, vol.embedding)
        results.append({"volunteer": vol, "score": score})
        
    
    results.sort(key=lambda x: x['score'], reverse=True)
    top_matches = results[:top_n]
    
    
    final_output = []
    for match in top_matches:
        vol = match["volunteer"]
        reasoning = generate_explainable_reasoning(task_text, vol)
        
        final_output.append({
            "volunteer_id": vol.id,
            "name": vol.name,
            "match_score_percent": round(match["score"] * 100, 1),
            "ai_reasoning": reasoning
        })
        
    return final_output


# LOCAL VALIDATION TEST

if __name__ == "__main__":
    print(f"{'='*20} RUNNING SEMANTIC MATCHING TEST {'='*20}\n")
    
    db_volunteers = [
        Volunteer(id="v1", name="Иван", bio="Люблю работать руками, часто сажаю деревья на даче.", skills=["Садоводство", "Физическая сила"]),
        Volunteer(id="v2", name="Анна", bio="Профессиональный SMM-специалист. Пишу посты, делаю крутые фото.", skills=["Копирайтинг", "Фотография"]),
        Volunteer(id="v3", name="Сергей", bio="Эко-активист, разбираюсь в переработке пластика и логистике.", skills=["Сортировка мусора", "Вождение"])
    ]
    
    test_task = "Нам нужны крепкие ребята для высадки аллеи саженцев в центральном парке."
    print(f"📌 ЗАДАЧА: {test_task}\n")
    print("⏳ Вычисляем (занимает пару секунд)...\n")
    
    matches = find_best_volunteers(test_task, db_volunteers, top_n=2)
    
    print("🏆 РЕЗУЛЬТАТ:")
    print(json.dumps(matches, indent=2, ensure_ascii=False))