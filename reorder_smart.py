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

def break_cycles_in_group(group: List[str], graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Разрывает циклы в группе вопросов"""
    cycles = find_cycles(graph)
    
    if not cycles:
        return graph
    
    # Создаем копию графа
    broken_graph = {k: v.copy() for k, v in graph.items()}
    
    # Разрываем циклы в группе
    for cycle in cycles:
        if len(cycle) > 1:
            # Удаляем последнюю зависимость в цикле
            last_node = cycle[-2]  # cycle[-1] == cycle[0] из-за замыкания
            first_node = cycle[0]
            if first_node in broken_graph[last_node]:
                print(f"  Разрываю цикл в группе: {last_node} -> {first_node}")
                broken_graph[last_node].discard(first_node)
    
    return broken_graph

def group_by_dependency_level(questions: List[Dict]) -> List[List[Dict]]:
    """Группирует вопросы по уровням зависимостей"""
    graph = build_dependency_graph(questions)
    question_dict = {q['id']: q for q in questions}
    
    # Находим циклы
    cycles = find_cycles(graph)
    print(f"Найдено {len(cycles)} циклов:")
    for i, cycle in enumerate(cycles):
        print(f"  Цикл {i+1}: {' -> '.join(cycle)}")
    
    # Разрываем циклы
    broken_graph = break_cycles_in_group(list(graph.keys()), graph)
    
    # Группируем по уровням зависимостей
    levels = []
    remaining = set(graph.keys())
    
    while remaining:
        # Находим вопросы без зависимостей в оставшихся
        current_level = []
        for question_id in list(remaining):
            dependencies = broken_graph.get(question_id, set())
            if not dependencies or all(dep not in remaining for dep in dependencies):
                current_level.append(question_id)
        
        if not current_level:
            # Если не можем найти независимые вопросы, берем все оставшиеся
            current_level = list(remaining)
        
        # Добавляем вопросы текущего уровня
        level_questions = [question_dict[qid] for qid in current_level if qid in question_dict]
        levels.append(level_questions)
        
        # Удаляем обработанные вопросы
        remaining -= set(current_level)
    
    return levels

def reorder_questions_smart(questions: List[Dict]) -> List[Dict]:
    """Переупорядочивает вопросы умным способом"""
    # Группируем по уровням зависимостей
    levels = group_by_dependency_level(questions)
    
    # Объединяем все уровни
    reordered = []
    for i, level in enumerate(levels):
        print(f"Уровень {i+1}: {[q['id'] for q in level]}")
        reordered.extend(level)
    
    return reordered

def main():
    input_file = 'public/q3.json'
    output_file = 'public/q3.json'
    
    print(f"Загружаю вопросы из {input_file}...")
    data = load_questions(input_file)
    
    print(f"Найдено {len(data['questions'])} вопросов")
    
    # Переупорядочиваем вопросы
    print("\nПереупорядочиваю вопросы умным способом...")
    reordered_questions = reorder_questions_smart(data['questions'])
    
    # Обновляем данные
    data['questions'] = reordered_questions
    
    # Сохраняем результат
    print(f"\nСохраняю результат в {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Готово!")

if __name__ == "__main__":
    main()
