#!/usr/bin/env python3
import json
from typing import Dict, List, Set

def load_questions(file_path: str) -> Dict:
    """Загружает вопросы из JSON файла"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def count_dependencies(question: Dict, all_questions: List[Dict]) -> int:
    """Подсчитывает количество зависимостей для вопроса"""
    if 'related_to' not in question:
        return 0
    
    question_ids = {q['id'] for q in all_questions}
    dependencies = 0
    
    for related_id in question['related_to']:
        if related_id in question_ids:
            dependencies += 1
    
    return dependencies

def reorder_by_dependency_count(questions: List[Dict]) -> List[Dict]:
    """Переупорядочивает вопросы по количеству зависимостей (от меньшего к большему)"""
    # Подсчитываем зависимости для каждого вопроса
    questions_with_deps = []
    for question in questions:
        dep_count = count_dependencies(question, questions)
        questions_with_deps.append((question, dep_count))
    
    # Сортируем по количеству зависимостей
    questions_with_deps.sort(key=lambda x: x[1])
    
    # Возвращаем только вопросы
    return [q[0] for q in questions_with_deps]

def main():
    input_file = 'public/q3.json'
    output_file = 'public/q3.json'
    
    print(f"Загружаю вопросы из {input_file}...")
    data = load_questions(input_file)
    
    print(f"Найдено {len(data['questions'])} вопросов")
    
    # Переупорядочиваем вопросы
    print("\nПереупорядочиваю вопросы по количеству зависимостей...")
    reordered_questions = reorder_by_dependency_count(data['questions'])
    
    # Выводим статистику
    print("\nСтатистика зависимостей:")
    for i, question in enumerate(reordered_questions):
        dep_count = count_dependencies(question, reordered_questions)
        deps = question.get('related_to', [])
        print(f"{i+1:2d}. {question['id']} - {dep_count} зависимостей: {deps}")
    
    # Обновляем данные
    data['questions'] = reordered_questions
    
    # Сохраняем результат
    print(f"\nСохраняю результат в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Готово!")

if __name__ == "__main__":
    main()
