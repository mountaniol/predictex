#!/usr/bin/env python3
"""
Тест исправлений WebSearch
"""
import requests
import json

def test_websearch(question_id, answer, all_answers=None):
    """Тестирует WebSearch для конкретного вопроса"""
    
    url = "http://localhost:3001/api/simple-evaluate.mjs"
    
    payload = {
        "questionId": question_id,
        "allAnswers": all_answers or {question_id: answer}
    }
    
    print(f"\n{'='*60}")
    print(f"Testing: {question_id}")
    print(f"Answer: {answer}")
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Score: {result.get('score')}")
        print(f"Explanation preview: {result.get('explanation', '')[:200]}...")
        
        # Проверяем, есть ли признаки WebSearch в объяснении
        explanation = result.get('explanation', '')
        if any(keyword in explanation.lower() 
               for keyword in ['according to', 'based on', 'источник', 'search', 'found']):
            print("🔍 WebSearch likely performed!")
        else:
            print("⚠️ WebSearch might not have been performed")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

# Тестовые случаи
if __name__ == "__main__":
    # Тест 1: Стратегический вопрос
    test_websearch(
        "SG01",
        ["declining_sales", "increased_competition"],
        {
            "MET.LOC": "San Francisco, CA",
            "SG01": ["declining_sales", "increased_competition"]
        }
    )
    
    # Тест 2: Вопрос с текстовым ответом
    test_websearch(
        "SG02",
        "We use AI and machine learning for predictive analytics",
        {
            "MET.LOC": "New York, NY",
            "MET.INDUSTRY": "FinTech",
            "SG02": "We use AI and machine learning for predictive analytics"
        }
    )
    
    # Тест 3: Вопрос с существующим ID
    test_websearch(
        "SG03A",
        "We have strong competitive advantages in our market segment",
        {
            "MET.LOC": "London, UK",
            "SG03A": "We have strong competitive advantages in our market segment"
        }
    )
    
    print("\n" + "="*60)
    print("Testing complete!")