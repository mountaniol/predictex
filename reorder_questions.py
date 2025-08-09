#!/usr/bin/env python3
import json
import sys
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

def load_questions(file_path: str) -> Dict:
    """Загружает вопросы из JSON файла"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_dependency_graph(questions: List[Dict]) -> Dict[str, Set[str]]:
    """Строит граф зависимостей между вопросами"""
    graph = defaultdict(set)
    question_ids = set()
    
    # Собираем все ID вопросов
    for question in questions:
        question_ids.add(question['id'])
    
    # Строим граф зависимостей
    for question in questions:
        question_id = question['id']
        if 'related_to' in question:
            for related_id in question['related_to']:
                if related_id in question_ids:
                    graph[question_id].add(related_id)
    
    return dict(graph)

def topological_sort(graph: Dict[str, Set[str]]) -> List[str]:
    """Выполняет топологическую сортировку графа зависимостей"""
    # Вычисляем входящие степени для каждого узла
    in_degree = defaultdict(int)
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] += 1
    
    # Находим узлы без входящих рёбер
    queue = deque([node for node in graph if in_degree[node] == 0])
    result = []
    
    while queue:
        node = queue.popleft()
        result.append(node)
        
        # Уменьшаем входящие степени соседей
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Проверяем на циклы
    if len(result) != len(graph):
        print("ВНИМАНИЕ: Обнаружены циклические зависимости!")
        return list(graph.keys())  # Возвращаем исходный порядок
    
    return result

def reorder_questions(questions: List[Dict]) -> List[Dict]:
    """Переупорядочивает вопросы на основе зависимостей"""
    # Строим граф зависимостей
    graph = build_dependency_graph(questions)
    
    # Выполняем топологическую сортировку
    sorted_ids = topological_sort(graph)
    
    # Создаем словарь для быстрого поиска вопросов по ID
    questions_dict = {q['id']: q for q in questions}
    
    # Переупорядочиваем вопросы
    reordered = []
    
    # Сначала добавляем вопросы в правильном порядке
    for question_id in sorted_ids:
        if question_id in questions_dict:
            reordered.append(questions_dict[question_id])
    
    # Добавляем вопросы, которые не имеют зависимостей
    for question in questions:
        if question['id'] not in graph:
            reordered.append(question)
    
    return reordered

def main():
    input_file = 'public/q3.json'
    output_file = 'public/q3.json'
    
    print(f"Загружаю вопросы из {input_file}...")
    data = load_questions(input_file)
    
    print(f"Найдено {len(data['questions'])} вопросов")
    
    # Анализируем зависимости
    graph = build_dependency_graph(data['questions'])
    print(f"Найдено {len(graph)} вопросов с зависимостями")
    
    # Выводим зависимости для отладки
    print("\nЗависимости:")
    for question_id, dependencies in graph.items():
        print(f"  {question_id} -> {list(dependencies)}")
    
    # Переупорядочиваем вопросы
    print("\nПереупорядочиваю вопросы...")
    reordered_questions = reorder_questions(data['questions'])
    
    # Обновляем данные
    data['questions'] = reordered_questions
    
    # Сохраняем результат
    print(f"Сохраняю результат в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Готово!")

if __name__ == "__main__":
    main()
