"""
Классификатор поисковых запросов для выбора оптимального провайдера
"""
import re
from typing import Dict, Any, List, Optional
import logging
from .search_models import SearchQuery

logger = logging.getLogger(__name__)


class QueryClassifier:
    """Классифицирует запросы для выбора оптимального провайдера"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.rules = self._load_classification_rules()
        
    def classify(self, query: SearchQuery) -> Dict[str, Any]:
        """
        Классифицировать запрос
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Словарь с результатами классификации:
            {
                "primary_type": str,  # "factual", "current", "general"
                "confidence": float,  # 0.0 - 1.0
                "suggested_providers": List[str],
                "reasoning": str
            }
        """
        text_lower = query.text.lower()
        
        # Подсчет очков для каждого типа
        scores = {
            "factual": 0.0,
            "current": 0.0,
            "general": 0.0
        }
        
        reasoning = []
        
        # Проверка ключевых слов и паттернов
        for query_type, rules in self.rules.items():
            keywords_found = []
            patterns_matched = []
            
            # Проверка ключевых слов
            for keyword in rules.get("keywords", []):
                if keyword in text_lower:
                    scores[query_type] += rules.get("weight", 0.5)
                    keywords_found.append(keyword)
                    
            # Проверка паттернов
            for pattern in rules.get("patterns", []):
                if re.search(pattern, text_lower):
                    scores[query_type] += rules.get("weight", 0.5)
                    patterns_matched.append(pattern)
                    
            if keywords_found or patterns_matched:
                reasoning.append(f"{query_type}: keywords={keywords_found}, patterns={patterns_matched}")
        
        # Дополнительные проверки
        temporal_markers = self._extract_temporal_markers(query.text)
        if temporal_markers:
            scores["current"] += 0.3 * len(temporal_markers)
            reasoning.append(f"temporal markers: {temporal_markers}")
            
        named_entities = self._extract_named_entities(query.text)
        if named_entities:
            scores["factual"] += 0.2 * len(named_entities)
            reasoning.append(f"named entities: {named_entities}")
        
        # Определение основного типа
        total_score = sum(scores.values())
        if total_score == 0:
            primary_type = "general"
            confidence = 0.5
        else:
            primary_type = max(scores, key=scores.get)
            confidence = scores[primary_type] / total_score
        
        # Выбор провайдеров
        suggested_providers = self._select_providers_for_type(primary_type, confidence)
        
        return {
            "primary_type": primary_type,
            "confidence": confidence,
            "suggested_providers": suggested_providers,
            "reasoning": "; ".join(reasoning) if reasoning else "No specific indicators found",
            "scores": scores
        }
        
    def _load_classification_rules(self) -> Dict[str, Any]:
        """Загрузить правила классификации"""
        return {
            "factual": {
                "keywords": [
                    "что такое", "кто такой", "определение", "история",
                    "биография", "значение", "понятие", "термин",
                    "объяснить", "расскажи о", "информация о"
                ],
                "patterns": [
                    r"\bчто\s+такое\b", r"\bкто\s+такой\b", 
                    r"\bопределение\b", r"\bwhat\s+is\b",
                    r"\bwho\s+is\b", r"\bdefine\b", r"\bexplain\b"
                ],
                "weight": 0.8
            },
            "current": {
                "keywords": [
                    "новости", "сегодня", "вчера", "текущий", "последний",
                    "актуальный", "сейчас", "недавно", "события",
                    "обновления", "свежий", "последние новости"
                ],
                "patterns": [
                    r"\b(today|сегодня|yesterday|вчера|current|текущий|latest|последний|recent|недавно)\b",
                    r"\b(news|новости|события|updates|обновления)\b",
                    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",  # даты в формате YYYY-MM-DD
                    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"  # даты в других форматах
                ],
                "weight": 0.9
            },
            "general": {
                "keywords": [
                    "найти", "поиск", "искать", "показать",
                    "где", "как", "почему", "зачем"
                ],
                "patterns": [
                    r"\b(find|найти|search|поиск|искать|show|показать)\b",
                    r"\b(where|где|how|как|why|почему)\b"
                ],
                "weight": 0.6
            }
        }
        
    def _extract_temporal_markers(self, text: str) -> List[str]:
        """Извлечь временные маркеры из текста"""
        temporal_patterns = [
            r'\b\d{4}\b',  # годы
            r'\b(январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])\b',
            r'\b(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)\b',
            r'\b(сегодня|вчера|завтра|позавчера|послезавтра)\b',
            r'\b(утром|днем|вечером|ночью)\b',
            r'\b(прошлый|этот|следующий|текущий)\s+(год|месяц|неделя|день)\b'
        ]
        
        markers = []
        text_lower = text.lower()
        
        for pattern in temporal_patterns:
            matches = re.findall(pattern, text_lower)
            markers.extend(matches)
            
        return list(set(markers))  # убираем дубликаты
        
    def _extract_named_entities(self, text: str) -> List[Dict[str, str]]:
        """
        Извлечь именованные сущности (упрощенная версия)
        В продакшене здесь можно использовать spaCy или другие NLP библиотеки
        """
        entities = []
        
        # Простое извлечение слов с заглавной буквы (кроме начала предложения)
        words = text.split()
        for i, word in enumerate(words):
            # Пропускаем первое слово и слова после точки
            if i > 0 and word[0].isupper() and not words[i-1].endswith('.'):
                # Проверяем, что это не просто предлог или союз
                if len(word) > 2 and word.lower() not in ['это', 'они', 'она', 'оно']:
                    entities.append({
                        "text": word,
                        "type": "potential_entity"
                    })
                    
        # Поиск известных паттернов (компании, персоны и т.д.)
        company_patterns = [
            r'\b(ООО|ОАО|ЗАО|ПАО|Inc|Ltd|LLC|Corp|Corporation)\s+[А-ЯA-Z][а-яa-z]+\b',
            r'\b[А-ЯA-Z][а-яa-z]+\s+(Inc|Ltd|LLC|Corp|Corporation)\b'
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append({
                    "text": match,
                    "type": "organization"
                })
                
        return entities
        
    def _select_providers_for_type(self, query_type: str, confidence: float) -> List[str]:
        """Выбрать провайдеров для типа запроса"""
        provider_map = {
            "factual": ["wikipedia", "duckduckgo"],
            "current": ["rss", "duckduckgo"],
            "general": ["duckduckgo", "wikipedia", "rss"]
        }
        
        # Если уверенность низкая, используем больше провайдеров
        if confidence < self.confidence_threshold:
            return ["duckduckgo", "wikipedia", "rss"]
            
        return provider_map.get(query_type, ["duckduckgo"])
        
    def get_classification_stats(self) -> Dict[str, Any]:
        """Получить статистику классификации"""
        return {
            "confidence_threshold": self.confidence_threshold,
            "rules_count": len(self.rules),
            "supported_types": list(self.rules.keys())
        }