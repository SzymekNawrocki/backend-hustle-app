import json
import logging
from typing import Dict, Any, Optional, List
from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"

    async def analyze_job(self, description: str, user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sends a request to Groq Cloud API to analyze a job description against a user profile.
        Returns a detailed JSON analysis optimized for frontend display.
        """
        system_prompt = (
            "Jesteś ekspertem HR i ATS. Twoim zadaniem jest porównanie opisu stanowiska z profilem użytkownika. "
            "Zwróć wynik WYŁĄCZNIE jako JSON. Nie dodawaj żadnego wstępu ani zakończenia. "
            "Format JSON musi zawierać:\n"
            "- match_score (Integer 0-100)\n"
            "- detailed_analysis (Object):\n"
            "  - tech_stack_match (List of { \"skill\": str, \"is_missing\": bool, \"importance\": \"high\"|\"medium\"|\"low\" })\n"
            "  - soft_skills_match (List of { \"skill\": str, \"match\": bool })\n"
            "  - salary_estimation (String or null)\n"
            "- missing_skills (List of strings)\n"
            "- cv_tips (List of strings)\n"
            "- pros (List of strings)\n"
            "- cons (List of strings)"
        )
        
        user_prompt = f"""
        PROFIL UŻYTKOWNIKA:
        {json.dumps(user_profile, indent=2)}
        
        OPIS STANOWISKA:
        {description}
        """

        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                response_format={"type": "json_object"},
            )
            
            result = chat_completion.choices[0].message.content
            return json.loads(result)
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {str(e)}")
            return None

    async def sync_profile_skills(self, raw_text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Uses Groq to extract skills and levels from raw text (e.g., CV).
        """
        system_prompt = (
            "Jesteś asystentem AI. Przeanalizuj podany tekst (CV lub opis doświadczenia) "
            "i wyodrębnij z niego umiejętności techniczne wraz z oszacowanym poziomem zaawansowania (1-10). "
            "Zwróć wynik WYŁĄCZNIE jako JSON w formacie: { \"skills\": [ { \"name\": str, \"level\": int } ] }"
        )

        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                model=self.model,
                response_format={"type": "json_object"},
            )
            
            result = json.loads(chat_completion.choices[0].message.content)
            return result.get("skills", [])
            
        except Exception as e:
            logger.error(f"Error syncing skills: {str(e)}")
            return None
