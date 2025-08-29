"""
Query classifier for selecting optimal provider
"""
import re
from typing import Dict, Any, List, Optional
import logging
from .search_models import SearchQuery

logger = logging.getLogger(__name__)


class QueryClassifier:
    """Classifies queries for selecting optimal provider"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.rules = self._load_classification_rules()
        
    def classify(self, query: SearchQuery) -> Dict[str, Any]:
        """
        Classify query
        
        Args:
            query: Search query
            
        Returns:
            Dictionary with classification results:
            {
                "primary_type": str,  # "factual", "current", "general"
                "confidence": float,  # 0.0 - 1.0
                "suggested_providers": List[str],
                "reasoning": str
            }
        """
        text_lower = query.text.lower()
        
        # Calculate scores for each type
        scores = {
            "factual": 0.0,
            "current": 0.0,
            "general": 0.0
        }
        
        reasoning = []
        
        # Check keywords and patterns
        for query_type, rules in self.rules.items():
            keywords_found = []
            patterns_matched = []
            
            # Check keywords
            for keyword in rules.get("keywords", []):
                if keyword in text_lower:
                    scores[query_type] += rules.get("weight", 0.5)
                    keywords_found.append(keyword)
                    
            # Check patterns
            for pattern in rules.get("patterns", []):
                if re.search(pattern, text_lower):
                    scores[query_type] += rules.get("weight", 0.5)
                    patterns_matched.append(pattern)
                    
            if keywords_found or patterns_matched:
                reasoning.append(f"{query_type}: keywords={keywords_found}, patterns={patterns_matched}")
        
        # Additional checks
        temporal_markers = self._extract_temporal_markers(query.text)
        if temporal_markers:
            scores["current"] += 0.3 * len(temporal_markers)
            reasoning.append(f"temporal markers: {temporal_markers}")
            
        named_entities = self._extract_named_entities(query.text)
        if named_entities:
            scores["factual"] += 0.2 * len(named_entities)
            reasoning.append(f"named entities: {named_entities}")
        
        # Determine primary type
        total_score = sum(scores.values())
        if total_score == 0:
            primary_type = "general"
            confidence = 0.5
        else:
            primary_type = max(scores, key=scores.get)
            confidence = scores[primary_type] / total_score
        
        # Select providers
        suggested_providers = self._select_providers_for_type(primary_type, confidence)
        
        return {
            "primary_type": primary_type,
            "confidence": confidence,
            "suggested_providers": suggested_providers,
            "reasoning": "; ".join(reasoning) if reasoning else "No specific indicators found",
            "scores": scores
        }
        
    def _load_classification_rules(self) -> Dict[str, Any]:
        """Load classification rules"""
        return {
            "factual": {
                "keywords": [
                    "what is", "who is", "definition", "history",
                    "biography", "meaning", "concept", "term",
                    "explain", "tell about", "information about"
                ],
                "patterns": [
                    r"\bwhat\s+is\b", r"\bwho\s+is\b", 
                    r"\bdefinition\b", r"\bdefine\b",
                    r"\bexplain\b", r"\bhistory\b", r"\bbiography\b"
                ],
                "weight": 0.8
            },
            "current": {
                "keywords": [
                    "news", "today", "yesterday", "current", "latest",
                    "actual", "now", "recently", "events",
                    "updates", "fresh", "latest news"
                ],
                "patterns": [
                    r"\b(today|yesterday|current|latest|recent|now)\b",
                    r"\b(news|events|updates|happening)\b",
                    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",  # dates in YYYY-MM-DD format
                    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"  # dates in other formats
                ],
                "weight": 0.9
            },
            "general": {
                "keywords": [
                    "find", "search", "look for", "show",
                    "where", "how", "why", "what for"
                ],
                "patterns": [
                    r"\b(find|search|look|show|discover)\b",
                    r"\b(where|how|why|when|what)\b"
                ],
                "weight": 0.6
            }
        }
        
    def _extract_temporal_markers(self, text: str) -> List[str]:
        """Extract temporal markers from text"""
        temporal_patterns = [
            r'\b\d{4}\b',  # years
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(today|yesterday|tomorrow)\b',
            r'\b(morning|afternoon|evening|night)\b',
            r'\b(last|this|next|current)\s+(year|month|week|day)\b'
        ]
        
        markers = []
        text_lower = text.lower()
        
        for pattern in temporal_patterns:
            matches = re.findall(pattern, text_lower)
            markers.extend(matches)
            
        return list(set(markers))  # remove duplicates
        
    def _extract_named_entities(self, text: str) -> List[Dict[str, str]]:
        """
        Extract named entities (simplified version)
        In production, spaCy or other NLP libraries can be used here
        """
        entities = []
        
        # Simple extraction of capitalized words (except at sentence start)
        words = text.split()
        for i, word in enumerate(words):
            # Skip first word and words after period
            if i > 0 and word[0].isupper() and not words[i-1].endswith('.'):
                # Check that it's not just a preposition or conjunction
                if len(word) > 2 and word.lower() not in ['the', 'this', 'that', 'these']:
                    entities.append({
                        "text": word,
                        "type": "potential_entity"
                    })
                    
        # Search for known patterns (companies, persons, etc.)
        company_patterns = [
            r'\b(Inc|Ltd|LLC|Corp|Corporation|Company|Co)\s+[A-Z][a-z]+\b',
            r'\b[A-Z][a-z]+\s+(Inc|Ltd|LLC|Corp|Corporation|Company|Co)\b'
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
        """Select providers for query type"""
        provider_map = {
            "factual": ["wikipedia", "duckduckgo"],
            "current": ["rss", "duckduckgo"],
            "general": ["duckduckgo", "wikipedia", "rss"]
        }
        
        # If confidence is low, use more providers
        if confidence < self.confidence_threshold:
            return ["duckduckgo", "wikipedia", "rss"]
            
        return provider_map.get(query_type, ["duckduckgo"])
        
    def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification statistics"""
        return {
            "confidence_threshold": self.confidence_threshold,
            "rules_count": len(self.rules),
            "supported_types": list(self.rules.keys())
        }