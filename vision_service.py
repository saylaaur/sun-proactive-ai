import os
import json
import io
from PIL import Image
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai

# 1. Загрузка ключа
load_dotenv("api_key.env")

# ==========================================
# СХЕМА ОТВЕТА (JSON Contract)
# ==========================================
class VerificationResult(BaseModel):
    is_verified: bool = Field(description="True, если фото доказывает выполнение задачи. Иначе False.")
    confidence: int = Field(description="Уверенность ИИ в решении (0-100%)")
    reasoning: str = Field(description="Краткое обоснование решения")
    is_fake_suspected: bool = Field(description="True, если похоже на фейк, сток или фото экрана")

# ==========================================
# ОСНОВНОЙ СЕРВИС
# ==========================================
def verify_task_completion(image_data: bytes, task_text: str) -> dict:
    """
    Принимает изображение в байтах и текст задачи.
    Возвращает вердикт верификации в формате JSON.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "CONFIG_ERROR", "details": "GEMINI_API_KEY не найден в api_key.env"}
        
    genai.configure(api_key=api_key)
    
    # Умный выбор модели (защита от ошибки 404)
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in all_models if 'flash' in m]
        selected_model = flash_models[0] if flash_models else all_models[0]
    except Exception as e:
        return {"error": "MODEL_ERROR", "details": f"Не удалось подобрать модель: {str(e)}"}

    model = genai.GenerativeModel(selected_model)
    
    try:
        # Конвертируем байты от бэкенда в картинку
        img = Image.open(io.BytesIO(image_data))
        
        system_prompt = f"""
        Ты — строгий AI-аудитор волонтерского фонда Sun Proactive. 
        Сравни фотоотчет волонтера с описанием задачи и вынеси вердикт.
        
        ЗАДАЧА: "{task_text}"
        
        ПРАВИЛА:
        1. Соответствует ли содержание фото сути задачи?
        2. Нет ли признаков мошенничества (фото экрана, пиксельная сетка, сток)?
        """
        
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=VerificationResult
        )
        
        response = model.generate_content(
            [system_prompt, img], 
            generation_config=generation_config
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        if "429" in str(e):
            return {"error": "QUOTA_EXCEEDED", "details": "Превышен лимит запросов API. Повторите позже."}
        return {"error": "VISION_ERROR", "details": str(e)}

# ==========================================
# ТЕСТОВЫЙ БЛОК (для локальной проверки бэкендером)
# ==========================================
if __name__ == "__main__":
    print("--- Тестирование модуля Vision ---")
    # Чтобы протестировать, бэкендеру нужно положить картинку test.jpg рядом с файлом
    try:
        with open("test.jpg", "rb") as f:
            img_bytes = f.read()
        
        task = "Уборка мусора в лесу. На фото должны быть собранные мешки."
        print(f"Задача: {task}")
        print("Анализ...")
        
        result = verify_task_completion(img_bytes, task)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except FileNotFoundError:
        print("ℹ️ Для локального теста положите файл 'test.jpg' в эту же папку.")