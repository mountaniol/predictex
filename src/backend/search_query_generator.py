"""
AI-powered search query generator for intelligent search strategy
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from .ai_providers import get_ai_provider

logger = logging.getLogger(__name__)

# Define the absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class SearchQueryGenerator:
    """
    AI-powered generator for creating intelligent search queries
    based on question context and user answers
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the search query generator
        
        Args:
            config: Backend configuration
        """
        self.config = config
        self.ai_provider = get_ai_provider(config)
        self.search_prompt = self._load_search_prompt()
        
        # Get AI model configuration
        ai_provider_type = config.get("ai_provider", "openai")
        if ai_provider_type == "ollama":
            provider_config = config.get("ollama", {})
            self.model = provider_config.get("model")
        else:
            provider_config = config.get("openai", {})
            self.model = provider_config.get("simple_evaluate_model", "gpt-4-1106-preview")
            
        self.temperature = 0.3  # Lower temperature for more consistent query generation
        self.max_tokens = 2048  # Enough for detailed search strategy
        
    def _load_search_prompt(self) -> str:
        """Load the search query generation prompt"""
        prompt_path = os.path.join(PROJECT_ROOT, 'public', 'questions', 'search-query-prompt.txt')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load search query prompt: {e}")
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """Fallback prompt if file loading fails"""
        return """
        You are a search query generator. Given a question and answer, 
        generate relevant search queries to verify and enrich the information.
        
        Return a JSON object with:
        - analysis_goal: what you want to verify
        - search_queries: array of query objects with query, sources, purpose
        - total_searches: number of queries
        """
    
    def generate_search_strategy(self, 
                                question: Dict[str, Any],
                                answer: Any,
                                all_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an AI-powered search strategy for the given question and answer
        
        Args:
            question: Question object with text, id, type, etc.
            answer: User's answer to the question
            all_answers: All answers for context
            
        Returns:
            Search strategy with queries and source selections
        """
        try:
            # Build context for AI
            context = self._build_context(question, answer, all_answers)
            
            # Create the prompt for AI
            user_prompt = f"""
Based on the following business evaluation context, generate search queries to verify and enrich the assessment:

QUESTION: {question.get('text', '')}
QUESTION ID: {question.get('id', '')}
QUESTION TYPE: {question.get('question_type', '')}

USER'S ANSWER: {self._format_answer(answer, question)}

BUSINESS CONTEXT:
- Location: {all_answers.get('MET.LOC', 'Not specified')}
- Industry: {all_answers.get('MET.IND', 'Not specified')}
- Company Size: {all_answers.get('MET.SIZE', 'Not specified')}
- Additional Context: {context.get('additional_context', '')}

Generate search queries following the instructions in the system prompt.
Focus on finding information that will help assess the risk level of this answer.
            """
            
            # Call AI provider
            messages = [
                {"role": "system", "content": self.search_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            logger.info(f"🔍 [SEARCH GENERATOR] Generating search strategy for question {question.get('id')}")
            
            response = self.ai_provider.chat_completion(
                messages=messages,
                model=self.model,
                response_format={"type": "json_object"},
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse the response
            search_strategy = json.loads(response['content'])
            
            logger.info(f"🔍 [SEARCH GENERATOR] Generated {search_strategy.get('total_searches', 0)} search queries")
            
            # Validate and enhance the strategy
            return self._validate_and_enhance_strategy(search_strategy, question, answer)
            
        except Exception as e:
            logger.error(f"Failed to generate search strategy: {e}")
            # Return a basic fallback strategy
            return self._get_fallback_strategy(question, answer, all_answers)
    
    def _build_context(self, question: Dict, answer: Any, all_answers: Dict) -> Dict:
        """Build contextual information for search generation"""
        context = {
            'question_cluster': question.get('cluster_name', ''),
            'has_dependencies': bool(question.get('ai_context', {}).get('include_answers')),
            'answer_type': type(answer).__name__,
            'additional_context': ''
        }
        
        # Add dependent answers context
        if question.get('ai_context', {}).get('include_answers'):
            deps = []
            for dep_id in question['ai_context']['include_answers']:
                if dep_id in all_answers:
                    deps.append(f"{dep_id}: {all_answers[dep_id]}")
            if deps:
                context['additional_context'] = "Related answers: " + "; ".join(deps)
        
        return context
    
    def _format_answer(self, answer: Any, question: Dict) -> str:
        """Format answer for display in prompt"""
        if isinstance(answer, list):
            # For multi-choice, get labels
            labels = []
            for code in answer:
                if code == 'other':
                    labels.append('Other (custom text)')
                else:
                    for opt in question.get('options', []):
                        if opt['code'] == code:
                            labels.append(opt['label'])
                            break
            return ", ".join(labels) if labels else str(answer)
        else:
            return str(answer)
    
    def _validate_and_enhance_strategy(self, 
                                      strategy: Dict,
                                      question: Dict,
                                      answer: Any) -> Dict:
        """Validate and enhance the AI-generated strategy"""
        
        # Ensure required fields exist
        if 'search_queries' not in strategy:
            strategy['search_queries'] = []
        
        if 'total_searches' not in strategy:
            strategy['total_searches'] = len(strategy.get('search_queries', []))
        
        # Limit to 20 searches as per specification
        if len(strategy['search_queries']) > 20:
            strategy['search_queries'] = strategy['search_queries'][:20]
            strategy['total_searches'] = 20
        
        # Validate each query
        valid_sources = [
            'WEB_SEARCH', 'WIKIPEDIA', 'NEWS_RSS', 'STATISTICS',
            'INDUSTRY_REPORTS', 'GOVERNMENT_DATA', 'ACADEMIC', 'LOCAL_BUSINESS'
        ]
        
        for query in strategy['search_queries']:
            # Ensure all required fields
            if 'query' not in query:
                query['query'] = ''
            if 'sources' not in query:
                query['sources'] = ['WEB_SEARCH']
            if 'priority' not in query:
                query['priority'] = 2
                
            # Validate sources
            query['sources'] = [s for s in query['sources'] if s in valid_sources]
            if not query['sources']:
                query['sources'] = ['WEB_SEARCH']
            
            # Ensure priority is 1-3
            query['priority'] = max(1, min(3, query.get('priority', 2)))
        
        # Add metadata
        strategy['question_id'] = question.get('id', '')
        strategy['generated_by'] = 'AI'
        
        return strategy
    
    def _get_fallback_strategy(self, 
                              question: Dict,
                              answer: Any,
                              all_answers: Dict) -> Dict:
        """Generate a basic fallback search strategy"""
        
        # Extract key terms from answer
        search_terms = []
        if isinstance(answer, str):
            # Simple keyword extraction
            words = answer.split()
            search_terms = [w for w in words if len(w) > 3][:3]
        elif isinstance(answer, list):
            search_terms = answer[:2]
        
        # Build basic query
        location = all_answers.get('MET.LOC', '')
        industry = all_answers.get('MET.IND', '')
        
        base_query = ' '.join(search_terms)
        if location:
            base_query += f" {location.split(',')[0]}"
        if industry:
            base_query += f" {industry}"
        
        return {
            'analysis_goal': 'Verify and contextualize user answer',
            'search_queries': [
                {
                    'query': base_query + ' industry trends 2024',
                    'sources': ['WEB_SEARCH', 'NEWS_RSS'],
                    'purpose': 'Find current industry context',
                    'priority': 1,
                    'expected_insight': 'Industry trends and market conditions'
                },
                {
                    'query': base_query + ' statistics data',
                    'sources': ['WEB_SEARCH', 'WIKIPEDIA'],
                    'purpose': 'Find statistical backing',
                    'priority': 2,
                    'expected_insight': 'Quantitative data for validation'
                }
            ],
            'total_searches': 2,
            'search_strategy': 'focused',
            'question_id': question.get('id', ''),
            'generated_by': 'fallback'
        }
    
    def map_sources_to_providers(self, sources: List[str]) -> List[str]:
        """
        Map abstract source types to actual provider implementations
        
        Args:
            sources: List of source types (e.g., ['WEB_SEARCH', 'STATISTICS'])
            
        Returns:
            List of provider names (e.g., ['duckduckgo', 'wikipedia'])
        """
        # Current mapping (will expand as we add more providers)
        source_to_provider_map = {
            'WEB_SEARCH': 'duckduckgo',
            'WIKIPEDIA': 'wikipedia',
            'NEWS_RSS': 'rss',
            'STATISTICS': 'duckduckgo',  # For now, until we have dedicated stats provider
            'INDUSTRY_REPORTS': 'duckduckgo',  # For now
            'GOVERNMENT_DATA': 'duckduckgo',  # For now
            'ACADEMIC': 'wikipedia',  # Wikipedia has some academic content
            'LOCAL_BUSINESS': 'duckduckgo'  # For now
        }
        
        providers = []
        for source in sources:
            provider = source_to_provider_map.get(source)
            if provider and provider not in providers:
                providers.append(provider)
        
        # Default to duckduckgo if no valid mapping
        if not providers:
            providers = ['duckduckgo']
            
        return providers