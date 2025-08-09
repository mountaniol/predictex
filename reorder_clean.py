#!/usr/bin/env python3
import json
from typing import Dict, List, Set

def load_questions(file_path: str) -> Dict:
    """Загружает вопросы из JSON файла"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_cyclic_dependencies(questions: List[Dict]) -> List[Dict]:
    """Очищает циклические зависимости из вопросов"""
    # Список всех ID вопросов
    question_ids = {q['id']: i for i, q in enumerate(questions)}
    
    # Создаем копию вопросов
    cleaned_questions = []
    
    for question in questions:
        question_copy = question.copy()
        
        if 'related_to' in question_copy:
            # Фильтруем зависимости, оставляя только те, которые не создают циклы
            valid_dependencies = []
            
            for dep_id in question_copy['related_to']:
                if dep_id in question_ids:
                    # Проверяем, что зависимость идет раньше в списке
                    if question_ids[dep_id] < question_ids[question_copy['id']]:
                        valid_dependencies.append(dep_id)
                    else:
                        print(f"Удаляю циклическую зависимость: {question_copy['id']} -> {dep_id}")
            
            if valid_dependencies:
                question_copy['related_to'] = valid_dependencies
            else:
                # Удаляем поле related_to, если нет валидных зависимостей
                del question_copy['related_to']
        
        cleaned_questions.append(question_copy)
    
    return cleaned_questions

def main():
    input_file = 'public/q3.json'
    output_file = 'public/q3.json'
    
    print(f"Загружаю вопросы из {input_file}...")
    data = load_questions(input_file)
    
    print(f"Найдено {len(data['questions'])} вопросов")
    
    # Очищаем циклические зависимости
    print("\nОчищаю циклические зависимости...")
    cleaned_questions = clean_cyclic_dependencies(data['questions'])
    
    # Обновляем данные
    data['questions'] = cleaned_questions
    
    # Сохраняем результат
    print(f"\nСохраняю результат в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Готово!")

if __name__ == "__main__":
    main()
