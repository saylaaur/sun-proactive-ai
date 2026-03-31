import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai


load_dotenv("api_key.env")

# DATA CONTRACT 
class SocialTaskDraft(BaseModel):
    title: Optional[str] = Field(description="Название социальной задачи")
    date_time: Optional[str] = Field(description="Дата и время проведения")
    location: Optional[str] = Field(description="Место проведения или адрес")
    
    hard_skills: List[str] = Field(description="Список необходимых твердых навыков")
    soft_skills: List[str] = Field(description="Список мягких навыков")
    
    volunteers_needed: Optional[int] = Field(description="Количество волонтеров")
    is_complete: bool = Field(description="Готовность задачи к публикации")
    question_for_user: Optional[str] = Field(description="Уточняющий вопрос от ИИ")

# AI INTERVIEWER ENGINE 
def process_curator_input(user_text: str) -> dict:
    """
    Обрабатывает ввод куратора через Gemini 2.5 Flash.
    Возвращает валидированный JSON-объект.
    """
    
    api_key = None
    try:
        from google.colab import userdata
        api_key = userdata.get('GEMINI_API_KEY')
    except (ImportError, Exception):
        pass
        
    
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {"error": "CONFIG_ERROR", "details": "GEMINI_API_KEY не найден ни в Colab, ни в api_key.env"}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        system_prompt = """
        Ты — AI-интервьюер платформы Sun Proactive. 
        Твоя задача — извлечь параметры социальной задачи из текста пользователя.
        
        ПРАВИЛА:
        1. Извлекай только реальные факты. Не галлюцинируй даты и адреса.
        2. Если отсутствуют title, location, date_time или volunteers_needed, установи is_complete=False.
        3. Если is_complete=False, сформируй один уточняющий вопрос в поле question_for_user.
        4. Если все ключевые поля на месте, установи is_complete=True.
        """

        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=SocialTaskDraft
        )

        response = model.generate_content(
            f"{system_prompt}\n\nInput Text: {user_text}",
            generation_config=generation_config
        )

        return json.loads(response.text)

    except Exception as e:
        return {"error": "AI_RUNTIME_ERROR", "details": str(e)}


if __name__ == "__main__":
    print("--- Running AI Service Test ---")
    test_input = "Нам нужны люди на субботник в парке в эту субботу."
    result = process_curator_input(test_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))