#!/usr/bin/env python3
import json
from typing import Dict, List, Set
from collections import defaultdict

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

def break_all_cycles_aggressive(graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Агрессивно разрывает ВСЕ циклы в графе"""
    cycles = find_cycles(graph)
    
    if not cycles:
        return graph
    
    print(f"Найдено {len(cycles)} циклов:")
    for i, cycle in enumerate(cycles):
        print(f"  Цикл {i+1}: {' -> '.join(cycle)}")
    
    # Создаем копию графа
    broken_graph = {k: v.copy() for k, v in graph.items()}
    
    # Агрессивно разрываем все циклы
    while cycles:
        cycles = find_cycles(broken_graph)
        if not cycles:
            break
            
        print(f"Осталось {len(cycles)} циклов, агрессивно разрываю...")
        
        for cycle in cycles:
            if len(cycle) > 1:
                # Удаляем ВСЕ зависимости в цикле, кроме первой
                for i in range(1, len(cycle)):
                    prev_node = cycle[i-1]
                    curr_node = cycle[i]
                    if curr_node in broken_graph[prev_node]:
                        print(f"  Разрываю цикл: удаляю зависимость {prev_node} -> {curr_node}")
                        broken_graph[prev_node].discard(curr_node)
    
    return broken_graph

def reorder_questions_final(questions: List[Dict]) -> List[Dict]:
    """Финальное переупорядочивание вопросов"""
    # Строим граф зависимостей
    graph = build_dependency_graph(questions)
    
    # Агрессивно разрываем все циклы
    broken_graph = break_all_cycles_aggressive(graph)
    
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

def topological_sort(graph: Dict[str, Set[str]]) -> List[str]:
    """Выполняет топологическую сортировку графа зависимостей"""
    from collections import deque
    
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

def main():
    input_file = 'public/q3.json'
    output_file = 'public/q3.json'
    
    print(f"Загружаю вопросы из {input_file}...")
    data = load_questions(input_file)
    
    print(f"Найдено {len(data['questions'])} вопросов")
    
    # Переупорядочиваем вопросы
    print("\nПереупорядочиваю вопросы финальным способом...")
    reordered_questions = reorder_questions_final(data['questions'])
    
    # Обновляем данные
    data['questions'] = reordered_questions
    
    # Сохраняем результат
    print(f"\nСохраняю результат в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Готово!")

if __name__ == "__main__":
    main()
