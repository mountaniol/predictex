#!/usr/bin/env python3
import json
from typing import Dict, List, Set

def load_questions(file_path: str) -> Dict:
    """Загружает вопросы из JSON файла"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def verify_order(questions: List[Dict]) -> None:
    """Проверяет правильность порядка вопросов"""
    question_positions = {}
    
    # Записываем позиции всех вопросов
    for i, question in enumerate(questions):
        question_positions[question['id']] = i
    
    print("Проверка порядка вопросов:")
    print("=" * 50)
    
    violations = []
    
    for question in questions:
        question_id = question['id']
        current_pos = question_positions[question_id]
        
        if 'related_to' in question:
            for related_id in question['related_to']:
                if related_id in question_positions:
                    related_pos = question_positions[related_id]
                    if related_pos > current_pos:
                        violations.append({
                            'question': question_id,
                            'position': current_pos,
                            'depends_on': related_id,
                            'depends_position': related_pos
                        })
    
    if violations:
        print(f"НАЙДЕНО {len(violations)} НАРУШЕНИЙ ПОРЯДКА:")
        for violation in violations:
            print(f"  ❌ {violation['question']} (позиция {violation['position']}) "
                  f"зависит от {violation['depends_on']} (позиция {violation['depends_position']})")
    else:
        print("✅ Все зависимости соблюдены правильно!")
    
    print(f"\nОбщий порядок вопросов:")
    print("-" * 30)
    for i, question in enumerate(questions):
        deps = question.get('related_to', [])
        deps_str = f" (зависит от: {', '.join(deps)})" if deps else ""
        print(f"{i+1:2d}. {question['id']}{deps_str}")

def main():
    input_file = 'public/q3.json'
    
    print(f"Загружаю вопросы из {input_file}...")
    data = load_questions(input_file)
    
    print(f"Найдено {len(data['questions'])} вопросов")
    
    verify_order(data['questions'])

if __name__ == "__main__":
    main()
