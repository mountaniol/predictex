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

def find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Находит все циклы в графе"""
    def dfs(node, path, visited, cycles):
        if node in path:
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return
        
        if node in visited:
            return
        
        visited.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            dfs(neighbor, path, visited, cycles)
        
        path.pop()
    
    cycles = []
    visited = set()
    
    for node in graph:
        if node not in visited:
            dfs(node, [], visited, cycles)
    
    return cycles

def break_all_cycles(graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Разрывает ВСЕ циклы в графе"""
    cycles = find_cycles(graph)
    
    if not cycles:
        return graph
    
    print(f"Найдено {len(cycles)} циклов:")
    for i, cycle in enumerate(cycles):
        print(f"  Цикл {i+1}: {' -> '.join(cycle)}")
    
    # Создаем копию графа
    broken_graph = {k: v.copy() for k, v in graph.items()}
    
    # Разрываем все циклы
    while cycles:
        cycles = find_cycles(broken_graph)
        if not cycles:
            break
            
        print(f"Осталось {len(cycles)} циклов, разрываю...")
        
        for cycle in cycles:
            if len(cycle) > 1:
                # Удаляем последнюю зависимость в цикле
                last_node = cycle[-2]  # cycle[-1] == cycle[0] из-за замыкания
                first_node = cycle[0]
                if first_node in broken_graph[last_node]:
                    print(f"  Разрываю цикл: удаляю зависимость {last_node} -> {first_node}")
                    broken_graph[last_node].discard(first_node)
    
    return broken_graph

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
        print("ВНИМАНИЕ: Все еще есть циклические зависимости!")
        return list(graph.keys())  # Возвращаем исходный порядок
    
    return result

def reorder_questions(questions: List[Dict]) -> List[Dict]:
    """Переупорядочивает вопросы на основе зависимостей"""
    # Строим граф зависимостей
    graph = build_dependency_graph(questions)
    
    # Разрываем ВСЕ циклы
    broken_graph = break_all_cycles(graph)
    
    # Выполняем топологическую сортировку
    sorted_ids = topological_sort(broken_graph)
    
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
