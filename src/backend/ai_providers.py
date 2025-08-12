"""
AI Provider abstraction for supporting multiple AI backends (OpenAI, Ollama, etc.)
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Generator
import time
from openai import OpenAI, RateLimitError, BadRequestError
import requests


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """
        Send a chat completion request to the AI provider
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters specific to the provider
            
        Returns:
            Dictionary with the response
        """
        pass
    
    @abstractmethod
    def stream_chat_completion(self, messages: list, **kwargs) -> Generator[str, None, None]:
        """
        Stream a chat completion request to the AI provider
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters specific to the provider
            
        Yields:
            Chunks of response text
        """
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider implementation"""
    
    def __init__(self, api_key: Optional[str] = None, project_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("REACT_APP_GPT_KEY")
        self.project_id = project_id or os.getenv("REACT_APP_PROJECT_ID")
        self.client = OpenAI(api_key=self.api_key, project=self.project_id)
    
    def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Send a chat completion request to OpenAI"""
        model = kwargs.get('model', 'gpt-4-1106-preview')
        temperature = kwargs.get('temperature', 0.3)
        max_tokens = kwargs.get('max_tokens', 1024)
        response_format = kwargs.get('response_format', None)
        
        request_params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if response_format:
            request_params["response_format"] = response_format
        
        completion = self.client.chat.completions.create(**request_params)
        return {
            "content": completion.choices[0].message.content,
            "model": completion.model,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens
            }
        }
    
    def stream_chat_completion(self, messages: list, **kwargs) -> Generator[str, None, None]:
        """Stream a chat completion request from OpenAI"""
        model = kwargs.get('model', 'gpt-4-1106-preview')
        temperature = kwargs.get('temperature', 0.3)
        max_tokens = kwargs.get('max_tokens', 1024)
        response_format = kwargs.get('response_format', None)
        
        request_params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        if response_format:
            request_params["response_format"] = response_format
        
        completion = self.client.chat.completions.create(**request_params)
        
        for chunk in completion:
            content = chunk.choices[0].delta.content
            if content:
                yield content


class OllamaProvider(AIProvider):
    """Ollama local model provider implementation"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        
    def _check_model_exists(self, model: str) -> bool:
        """Check if the model exists in Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(m['name'] == model for m in models)
            return False
        except:
            return False
    
    def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Send a chat completion request to Ollama"""
        model = kwargs.get('model', 'llama3.1:8b')
        temperature = kwargs.get('temperature', 0.3)
        max_tokens = kwargs.get('max_tokens', 1024)
        response_format = kwargs.get('response_format', None)
        
        # Check if model exists
        if not self._check_model_exists(model):
            raise ValueError(f"Model '{model}' not found in Ollama. Please pull it first with: ollama pull {model}")
        
        # Convert messages to Ollama format
        prompt = self._messages_to_prompt(messages)
        
        # Prepare request
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # If JSON response is required, add instruction
        if response_format and response_format.get('type') == 'json_object':
            data["format"] = "json"
            # Add JSON instruction to prompt if not already there
            if "JSON" not in prompt:
                data["prompt"] += "\n\nYou MUST respond with valid JSON only."
        
        # Send request
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=data,
            timeout=300  # 5 minutes timeout for long responses
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        return {
            "content": result['response'],
            "model": model,
            "usage": {
                "prompt_tokens": result.get('prompt_eval_count', 0),
                "completion_tokens": result.get('eval_count', 0),
                "total_tokens": result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
            }
        }
    
    def stream_chat_completion(self, messages: list, **kwargs) -> Generator[str, None, None]:
        """Stream a chat completion request from Ollama"""
        model = kwargs.get('model', 'llama3.1:8b')
        temperature = kwargs.get('temperature', 0.3)
        max_tokens = kwargs.get('max_tokens', 1024)
        response_format = kwargs.get('response_format', None)
        
        # Check if model exists
        if not self._check_model_exists(model):
            raise ValueError(f"Model '{model}' not found in Ollama. Please pull it first with: ollama pull {model}")
        
        # Convert messages to Ollama format
        prompt = self._messages_to_prompt(messages)
        
        # Prepare request
        data = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # If JSON response is required, add instruction
        if response_format and response_format.get('type') == 'json_object':
            data["format"] = "json"
            # Add JSON instruction to prompt if not already there
            if "JSON" not in prompt:
                data["prompt"] += "\n\nYou MUST respond with valid JSON only."
        
        # Send streaming request
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=data,
            stream=True,
            timeout=300
        )
        
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
        
        # Stream response chunks
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if 'response' in chunk:
                    yield chunk['response']
    
    def _messages_to_prompt(self, messages: list) -> str:
        """Convert OpenAI-style messages to a single prompt for Ollama"""
        prompt_parts = []
        
        for message in messages:
            role = message['role']
            content = message['content']
            
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"Human: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        # Add final assistant prompt if last message wasn't from assistant
        if messages and messages[-1]['role'] != 'assistant':
            prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)


def get_ai_provider(config: Dict[str, Any]) -> AIProvider:
    """
    Factory function to get the appropriate AI provider based on configuration
    
    Args:
        config: Configuration dictionary from app.config.json
        
    Returns:
        An instance of the appropriate AI provider
    """
    backend_config = config.get('Backend', {})
    provider_type = backend_config.get('ai_provider', 'openai')
    
    if provider_type == 'ollama':
        ollama_config = backend_config.get('ollama', {})
        base_url = ollama_config.get('base_url', 'http://localhost:11434')
        return OllamaProvider(base_url=base_url)
    elif provider_type == 'openai':
        return OpenAIProvider()
    else:
        raise ValueError(f"Unknown AI provider: {provider_type}")