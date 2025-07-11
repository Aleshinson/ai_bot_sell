import json
import asyncio
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from config import Config


class AISearchService:
    """Сервис для умного поиска AI-решений с помощью GPT"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None

    async def smart_search(self, user_query: str, announcements: List[Dict]) -> Dict:
        """
        Умный поиск AI-решений с помощью GPT

        Args:
            user_query: Запрос пользователя
            announcements: Список всех одобренных объявлений

        Returns:
            Dict с результатами поиска в формате:
            {
                "found": bool,
                "results": List[Dict],
                "explanation": str
            }
        """
        if not self.client:
            # Fallback на обычный поиск если нет API ключа
            return self._fallback_search(user_query, announcements)

        try:
            # Подготавливаем данные для GPT
            announcements_json = json.dumps([
                {
                    "id": ann["id"],
                    "bot_name": ann["bot_name"],
                    "bot_function": ann["bot_function"]
                }
                for ann in announcements
            ], ensure_ascii=False, indent=2)

            # Формируем промпт для GPT
            prompt = self._create_search_prompt(user_query, announcements_json)

            # Отправляем запрос к GPT
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты - эксперт по AI-решениям. Помогаешь пользователям найти подходящие AI-боты и решения."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )

            # Парсим ответ GPT
            gpt_response = response.choices[0].message.content
            return self._parse_gpt_response(gpt_response, announcements)

        except Exception as e:
            print(f"Ошибка при обращении к GPT: {e}")
            # Fallback на обычный поиск при ошибке
            return self._fallback_search(user_query, announcements)

    def _create_search_prompt(self, user_query: str, announcements_json: str) -> str:
        """Создание промпта для GPT"""
        return f"""
Пользователь ищет AI-решение с запросом: "{user_query}"

Доступные AI-решения:
{announcements_json}

Проанализируй запрос пользователя и найди наиболее подходящие AI-решения из списка.

Верни ответ СТРОГО в формате JSON:
{{
    "found": true/false,
    "results": [
        {{
            "id": номер_id,
            "relevance_score": оценка_от_1_до_10,
            "explanation": "краткое объяснение почему подходит"
        }}
    ],
    "general_explanation": "общее объяснение результатов поиска"
}}

Требования:
1. Если ничего не найдено, верни "found": false и пустой массив results
2. Сортируй результаты по relevance_score (от большего к меньшему)
3. Включай только решения с relevance_score >= 6
4. Максимум 5 результатов
5. Объяснения должны быть краткими (до 50 символов)
6. Отвечай ТОЛЬКО JSON, без дополнительного текста
"""

    def _parse_gpt_response(self, gpt_response: str, announcements: List[Dict]) -> Dict:
        """Парсинг ответа GPT и формирование результата"""
        try:
            # Очищаем ответ от возможных markdown блоков
            clean_response = gpt_response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()

            # Парсим JSON
            parsed = json.loads(clean_response)

            if not parsed.get("found", False) or not parsed.get("results"):
                return {
                    "found": False,
                    "results": [],
                    "explanation": parsed.get("general_explanation", "По вашему запросу ничего не найдено")
                }

            # Находим полные данные объявлений по ID
            announcement_map = {ann["id"]: ann for ann in announcements}
            full_results = []

            for result in parsed["results"]:
                ann_id = result["id"]
                if ann_id in announcement_map:
                    full_ann = announcement_map[ann_id].copy()
                    full_ann["relevance_score"] = result["relevance_score"]
                    full_ann["ai_explanation"] = result["explanation"]
                    full_results.append(full_ann)

            return {
                "found": True,
                "results": full_results,
                "explanation": parsed.get("general_explanation", "Найдены подходящие AI-решения")
            }

        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON от GPT: {e}")
            print(f"Ответ GPT: {gpt_response}")
            return self._fallback_search("", announcements)
        except Exception as e:
            print(f"Ошибка обработки ответа GPT: {e}")
            return self._fallback_search("", announcements)

    def _fallback_search(self, user_query: str, announcements: List[Dict]) -> Dict:
        """Обычный поиск как fallback"""
        if not user_query:
            return {
                "found": False,
                "results": [],
                "explanation": "Введите поисковый запрос"
            }

        query_lower = user_query.lower()
        results = []

        for ann in announcements:
            if (query_lower in ann["bot_name"].lower() or
                query_lower in ann["bot_function"].lower()):
                results.append(ann)

        return {
            "found": len(results) > 0,
            "results": results[:5],  # Максимум 5 результатов
            "explanation": f"Найдено {len(results)} решений по обычному поиску" if results else "Ничего не найдено"
        }
