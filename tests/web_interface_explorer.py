#!/usr/bin/env python3
"""
Исследователь структуры веб-интерфейса для понимания DOM и селекторов
"""
import time
import json
from typing import Dict, List, Any

class WebInterfaceExplorer:
    """Класс для исследования структуры веб-интерфейса"""
    
    def __init__(self, base_url: str = "http://192.168.1.50:3000"):
        self.base_url = base_url
        self.findings = {
            "page_structure": {},
            "form_elements": {},
            "question_flow": [],
            "selectors": {},
            "errors": []
        }
    
    def log_finding(self, category: str, key: str, value: Any):
        """Записывает найденную информацию"""
        if category not in self.findings:
            self.findings[category] = {}
        self.findings[category][key] = value
        print(f"📝 [{category}] {key}: {value}")
    
    def log_error(self, error: str):
        """Записывает ошибку"""
        self.findings["errors"].append(error)
        print(f"❌ Error: {error}")
    
    def save_findings(self, filename: str = "tests/web_interface_findings.json"):
        """Сохраняет результаты исследования"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.findings, f, indent=2, ensure_ascii=False)
        print(f"💾 Findings saved to {filename}")

def main():
    """Основная функция для исследования веб-интерфейса"""
    explorer = WebInterfaceExplorer()
    
    print("🔍 Начинаем исследование веб-интерфейса на http://192.168.1.50:3000")
    print("=" * 70)
    
    # Этот скрипт будет использоваться с browser_action для:
    # 1. Загрузки главной страницы
    # 2. Анализа структуры форм
    # 3. Поиска селекторов для полей
    # 4. Понимания flow между вопросами
    # 5. Определения как добраться до SG01
    
    explorer.log_finding("plan", "target_url", "http://192.168.1.50:3000")
    explorer.log_finding("plan", "target_question", "SG01 - Why are you selling now?")
    explorer.log_finding("plan", "target_answer", "Declining sales")
    explorer.log_finding("plan", "expected_score_range", "0-19 (critical risk)")
    
    print("\n📋 План исследования:")
    print("1. Загрузить главную страницу")
    print("2. Найти форму опросника")
    print("3. Определить селекторы для полей")
    print("4. Понять последовательность вопросов")
    print("5. Найти путь к SG01")
    print("6. Изучить механизм получения score/explanation")
    
    explorer.save_findings()
    
    return explorer

if __name__ == "__main__":
    main()