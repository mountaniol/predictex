#!/usr/bin/env python3
"""
Отладочный скрипт для WebSearch
"""
import requests
import json
import time

def debug_request(question_id, answer):
    """Делает отладочный запрос с детальной информацией"""
    
    url = "http://localhost:3001/api/simple-evaluate.mjs"
    
    payload = {
        "questionId": question_id,
        "allAnswers": {
            question_id: answer,
            "MET.LOC": "San Francisco, CA",  # Добавляем контекст
            "MET.INDUSTRY": "Technology"
        }
    }
    
    print(f"\n{'='*80}")
    print(f"🔍 DEBUG REQUEST: {question_id}")
    print(f"🔍 PAYLOAD: {json.dumps(payload, indent=2)}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"📊 STATUS: {response.status_code}")
        print(f"📊 DURATION: {duration:.2f}s")
        print(f"📊 HEADERS: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ RESPONSE SUCCESS:")
            print(f"  Score: {result.get('score')}")
            print(f"  Explanation Length: {len(result.get('explanation', ''))}")
            print(f"\n📝 EXPLANATION:")
            print(result.get('explanation', ''))
            
            # Анализируем на признаки WebSearch
            explanation = result.get('explanation', '').lower()
            search_indicators = [
                'according to', 'based on', 'источник', 'search', 'found',
                'web search', 'results', 'information found',
                'research shows', 'studies indicate', 'data suggests'
            ]
            
            found_indicators = [ind for ind in search_indicators if ind in explanation]
            
            if found_indicators:
                print(f"\n🔍 WebSearch INDICATORS FOUND: {found_indicators}")
            else:
                print(f"\n⚠️  NO WebSearch indicators detected")
                
        else:
            print(f"\n❌ ERROR RESPONSE:")
            print(response.text)
            
    except Exception as e:
        print(f"\n💥 REQUEST FAILED: {e}")

if __name__ == "__main__":
    print("🚀 Starting WebSearch Debug Tests...")
    
    # Тест с разными типами вопросов
    test_cases = [
        ("SG01", ["declining_sales"]),
        ("SG02", "We use AI and machine learning"),
        ("MET.LOC", "New York, NY")
    ]
    
    for question_id, answer in test_cases:
        debug_request(question_id, answer)
        time.sleep(1)  # Пауза между запросами
    
    print("\n🏁 Debug tests completed!")