import json
from typing import Dict, Any
from groq import AsyncGroq, RateLimitError, APIConnectionError
from app.core.config import settings
from app.core.exceptions import AIServiceError

class AIService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"

    async def _get_json_response(self, prompt: str, system_prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": f"{system_prompt}. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=temperature
            )
            raw = chat_completion.choices[0].message.content
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                raise AIServiceError("AI returned invalid response, try again", status_code=502)
        except AIServiceError:
            raise
        except (RateLimitError, APIConnectionError) as e:
            raise AIServiceError(f"AI service temporarily unavailable: {e}", status_code=503)
        except Exception as e:
            raise AIServiceError(f"AI analysis failure: {e}", status_code=503)


    async def parse_meal(self, text: str) -> Dict[str, Any]:
        system_prompt = "You are a nutritional expert. Extract calories (int), protein (float), carbs (float), and fat (float) from the meal description."
        return await self._get_json_response(text, system_prompt)

    async def analyze_job_fit(self, job_desc: str, cv_text: str) -> Dict[str, Any]:
        system_prompt = "You are a senior recruiter. Analyze the job description against the provided CV. Return match_score (int 0-100), matching_keywords (list), and missing_skills (list)."
        prompt = f"Job Description: {job_desc}\n\nUser CV: {cv_text}"
        return await self._get_json_response(prompt, system_prompt)

    async def generate_okr(self, idea: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a productivity expert. Generate a high-level goal based on the user's idea in ENGLISH. "
            "Return ONLY a valid JSON object with the following keys: "
            "'title' (string), "
            "'description' (string, max 2 sentences), "
            "'milestones' (list of 3-4 strings), "
            "'tasks' (list of 5-8 actionable small steps)."
        )
        prompt = f"Goal Idea: {idea}"
        return await self._get_json_response(prompt, system_prompt)

    async def parse_hustle_input(self, text: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a financial analyst for Hustle App. Your job is to extract structured data from text and categorize it. "
            "Return JSON: {amount: float, category: 'EXPENSES'|'HUSTLE'|'LIFESTYLE'|'INCOME', description: string}. "
            "Rules: if the expense is a course/book/gear -> HUSTLE. If it's food or rent/bills -> EXPENSES. If it's income/salary/transfer/bonus -> INCOME. Otherwise -> LIFESTYLE."
        )
        return await self._get_json_response(text, system_prompt, temperature=0)

ai_service = AIService()
