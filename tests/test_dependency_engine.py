"""
Comprehensive Test Suite for Dependency Engine Component
Following Test-Driven Development methodology for Task 1.2

This test suite provides complete coverage of the Dependency Engine component
before implementation (Red phase of TDD).

Test Coverage:
- Graph building from question configurations
- Topological sorting for evaluation order
- Circular dependency detection 
- Cascade detection for answer changes
- Missing dependency handling
- Edge cases: empty graphs, single nodes, complex chains
- Diamond dependencies, forest structures
- Self-dependency detection

Mathematical Properties Tested:
- DAG (Directed Acyclic Graph) validity
- Topological ordering correctness
- Transitive dependency closure
- Cycle detection algorithm correctness
- Graph connectivity analysis
"""

import pytest
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, patch


class TestDependencyEngine:
    """
    Core Dependency Engine functionality tests
    These tests will FAIL initially until DependencyEngine is implemented (TDD Red phase)
    """

    @pytest.fixture
    def dependency_engine(self):
        """Create DependencyEngine instance for testing"""
        # This import will fail initially - that's expected in TDD Red phase
        from src.backend.dependency_engine import DependencyEngine
        return DependencyEngine()

    @pytest.fixture
    def sample_questions(self) -> List[Dict[str, Any]]:
        """Sample question data with various dependency patterns"""
        return [
            {
                "id": "Q1",
                "text": "Basic question with no dependencies",
                "ai_context_include_answers": []
            },
            {
                "id": "Q2", 
                "text": "Question depending on Q1",
                "ai_context_include_answers": ["Q1"]
            },
            {
                "id": "Q3",
                "text": "Question depending on Q1 and Q2", 
                "ai_context_include_answers": ["Q1", "Q2"]
            },
            {
                "id": "Q4",
                "text": "Independent question",
                "ai_context_include_answers": []
            },
            {
                "id": "Q5",
                "text": "Question depending on Q4",
                "ai_context_include_answers": ["Q4"]
            }
        ]

    @pytest.fixture 
    def circular_questions(self) -> List[Dict[str, Any]]:
        """Questions with circular dependencies for testing cycle detection"""
        return [
            {
                "id": "A",
                "text": "Question A depends on B",
                "ai_context_include_answers": ["B"]
            },
            {
                "id": "B", 
                "text": "Question B depends on C",
                "ai_context_include_answers": ["C"]
            },
            {
                "id": "C",
                "text": "Question C depends on A (creates cycle)",
                "ai_context_include_answers": ["A"]
            }
        ]

    @pytest.fixture
    def diamond_questions(self) -> List[Dict[str, Any]]:
        """Diamond dependency pattern: Q1 -> Q2,Q3 -> Q4"""
        return [
            {
                "id": "Q1",
                "text": "Root question",
                "ai_context_include_answers": []
            },
            {
                "id": "Q2",
                "text": "Left branch depends on Q1",
                "ai_context_include_answers": ["Q1"]
            },
            {
                "id": "Q3", 
                "text": "Right branch depends on Q1",
                "ai_context_include_answers": ["Q1"]
            },
            {
                "id": "Q4",
                "text": "Converge point depends on Q2 and Q3",
                "ai_context_include_answers": ["Q2", "Q3"]
            }
        ]

    @pytest.fixture
    def forest_questions(self) -> List[Dict[str, Any]]:
        """Multiple independent dependency trees (forest structure)"""
        return [
            # Tree 1: A -> B -> C
            {"id": "A", "ai_context_include_answers": []},
            {"id": "B", "ai_context_include_answers": ["A"]},
            {"id": "C", "ai_context_include_answers": ["B"]},
            
            # Tree 2: X -> Y 
            {"id": "X", "ai_context_include_answers": []},
            {"id": "Y", "ai_context_include_answers": ["X"]},
            
            # Isolated node
            {"id": "Z", "ai_context_include_answers": []}
        ]

    def test_build_dependency_graph(self, dependency_engine, sample_questions):
        """
        Test: Correctly builds DAG from questions
        
        Verifies that the dependency engine can construct a proper directed
        acyclic graph from question configurations.
        
        Expected behavior:
        - Builds adjacency list representation 
        - Includes both forward and reverse mappings
        - Handles missing dependencies gracefully
        - Creates isolated nodes for independent questions
        """
        # Act
        dependency_engine.build_dependency_graph(sample_questions)
        
        # Assert: Graph structure is correct
        graph = dependency_engine.get_dependency_graph()
        
        # Q1 has no dependencies (root node)
        assert "Q1" in graph
        assert graph["Q1"] == []
        
        # Q2 depends on Q1
        assert "Q2" in graph  
        assert "Q1" in graph["Q2"]
        
        # Q3 depends on Q1 and Q2
        assert "Q3" in graph
        assert "Q1" in graph["Q3"]
        assert "Q2" in graph["Q3"]
        
        # Q4 is independent
        assert "Q4" in graph
        assert graph["Q4"] == []
        
        # Q5 depends on Q4
        assert "Q5" in graph
        assert "Q4" in graph["Q5"]

    def test_build_reverse_dependency_graph(self, dependency_engine, sample_questions):
        """
        Test: Builds reverse dependency graph for efficient cascade detection
        
        Verifies that the engine maintains a reverse mapping to quickly find
        which questions depend on a given question.
        """
        # Act
        dependency_engine.build_dependency_graph(sample_questions)
        
        # Assert: Reverse graph is correct
        reverse_graph = dependency_engine.get_reverse_dependency_graph()
        
        # Q1 is depended upon by Q2 and Q3
        assert "Q1" in reverse_graph
        assert "Q2" in reverse_graph["Q1"]
        assert "Q3" in reverse_graph["Q1"]
        
        # Q2 is depended upon by Q3
        assert "Q2" in reverse_graph
        assert "Q3" in reverse_graph["Q2"]
        
        # Q4 is depended upon by Q5
        assert "Q4" in reverse_graph
        assert "Q5" in reverse_graph["Q4"]
        
        # Q3 and Q5 have no dependents
        assert reverse_graph.get("Q3", []) == []
        assert reverse_graph.get("Q5", []) == []

    def test_topological_sort(self, dependency_engine, sample_questions):
        """
        Test: Returns valid evaluation order
        
        Verifies that topological sorting produces a valid evaluation order
        where all dependencies are evaluated before dependents.
        
        Mathematical property: For any edge (u,v) in the DAG, 
        u appears before v in the topological order.
        """
        # Arrange
        dependency_engine.build_dependency_graph(sample_questions)
        
        # Act
        evaluation_order = dependency_engine.get_topological_order()
        
        # Assert: Valid topological order
        assert len(evaluation_order) == 5
        assert set(evaluation_order) == {"Q1", "Q2", "Q3", "Q4", "Q5"}
        
        # Q1 must come before Q2 and Q3
        q1_pos = evaluation_order.index("Q1")
        q2_pos = evaluation_order.index("Q2") 
        q3_pos = evaluation_order.index("Q3")
        assert q1_pos < q2_pos
        assert q1_pos < q3_pos
        
        # Q2 must come before Q3
        assert q2_pos < q3_pos
        
        # Q4 must come before Q5
        q4_pos = evaluation_order.index("Q4")
        q5_pos = evaluation_order.index("Q5")
        assert q4_pos < q5_pos

    def test_circular_dependency_detection(self, dependency_engine, circular_questions):
        """
        Test: Detects and reports circular dependencies
        
        Verifies that the engine can detect cycles in the dependency graph
        and provide meaningful error information.
        
        Uses Depth-First Search with color marking:
        - White (0): Unvisited
        - Gray (1): Visiting (in current path)  
        - Black (2): Visited (completed)
        
        Cycle exists if we encounter a gray node during DFS.
        """
        # Act & Assert: Building graph with circular dependencies should raise error
        with pytest.raises(ValueError) as exc_info:
            dependency_engine.build_dependency_graph(circular_questions)
        
        error_message = str(exc_info.value)
        assert "circular dependency" in error_message.lower()
        assert "cycle detected" in error_message.lower()
        
        # Should identify the cycle participants
        assert "A" in error_message
        assert "B" in error_message  
        assert "C" in error_message

    def test_circular_dependency_detection_algorithm(self, dependency_engine, circular_questions):
        """
        Test: Circular dependency detection algorithm correctness
        
        Tests the specific algorithm used for cycle detection.
        """
        # Act: Attempt to detect cycles manually
        cycles = dependency_engine.detect_cycles(circular_questions)
        
        # Assert: Cycle is properly identified
        assert len(cycles) > 0
        
        # The cycle should contain all three nodes
        cycle = cycles[0]  # Get first detected cycle
        assert len(cycle) >= 3
        assert "A" in cycle
        assert "B" in cycle
        assert "C" in cycle

    def test_cascade_detection(self, dependency_engine, sample_questions):
        """
        Test: Identifies all affected questions when one changes
        
        Verifies that changing an answer triggers evaluation of all
        transitively dependent questions in the correct order.
        
        Mathematical property: Transitive closure of dependencies
        """
        # Arrange
        dependency_engine.build_dependency_graph(sample_questions)
        
        # Act: Q1 changes - should cascade to Q2 and Q3
        cascaded = dependency_engine.get_cascade_dependencies("Q1")
        
        # Assert: Correct cascade detection
        assert "Q2" in cascaded
        assert "Q3" in cascaded
        assert "Q4" not in cascaded  # Independent
        assert "Q5" not in cascaded  # Independent branch
        
        # Verify order: Q2 should come before Q3 in cascade
        assert cascaded.index("Q2") < cascaded.index("Q3")

    def test_cascade_detection_transitive(self, dependency_engine, sample_questions):
        """
        Test: Cascade detection includes transitive dependencies
        
        Tests that changes propagate through multiple levels of dependencies.
        """
        # Arrange: Create deeper dependency chain
        deep_questions = [
            {"id": "ROOT", "ai_context_include_answers": []},
            {"id": "L1", "ai_context_include_answers": ["ROOT"]},
            {"id": "L2", "ai_context_include_answers": ["L1"]},  
            {"id": "L3", "ai_context_include_answers": ["L2"]}
        ]
        
        dependency_engine.build_dependency_graph(deep_questions)
        
        # Act: ROOT changes - should cascade through all levels
        cascaded = dependency_engine.get_cascade_dependencies("ROOT")
        
        # Assert: All levels are included
        assert "L1" in cascaded
        assert "L2" in cascaded
        assert "L3" in cascaded
        
        # Verify correct order
        assert cascaded.index("L1") < cascaded.index("L2")
        assert cascaded.index("L2") < cascaded.index("L3")

    def test_missing_dependency_handling(self, dependency_engine):
        """
        Test: Gracefully handles missing dependencies
        
        Verifies that references to non-existent questions are handled
        appropriately without crashing the system.
        """
        # Arrange: Question with missing dependency
        questions_with_missing = [
            {"id": "Q1", "ai_context_include_answers": []},
            {"id": "Q2", "ai_context_include_answers": ["Q1", "MISSING_Q"]}
        ]
        
        # Act & Assert: Should handle missing dependencies gracefully
        dependency_engine.build_dependency_graph(questions_with_missing)
        
        # Missing dependencies should be logged but not crash
        graph = dependency_engine.get_dependency_graph()
        assert "Q1" in graph["Q2"]  # Valid dependency included
        
        # Get missing dependencies report
        missing_deps = dependency_engine.get_missing_dependencies()
        assert "MISSING_Q" in missing_deps

    def test_missing_dependency_warnings(self, dependency_engine):
        """
        Test: Missing dependencies generate appropriate warnings
        """
        # Arrange
        questions_with_missing = [
            {"id": "VALID", "ai_context_include_answers": ["INVALID1", "INVALID2"]}
        ]
        
        # Act
        with patch('logging.warning') as mock_warning:
            dependency_engine.build_dependency_graph(questions_with_missing)
            
        # Assert: Warnings were generated
        assert mock_warning.called
        warning_args = mock_warning.call_args_list
        warning_messages = [str(call[0]) for call in warning_args]
        
        assert any("INVALID1" in msg for msg in warning_messages)
        assert any("INVALID2" in msg for msg in warning_messages)

    def test_empty_graph(self, dependency_engine):
        """
        Test: Edge case - empty question list
        
        Verifies proper handling of empty input.
        """
        # Act
        dependency_engine.build_dependency_graph([])
        
        # Assert
        assert dependency_engine.get_dependency_graph() == {}
        assert dependency_engine.get_reverse_dependency_graph() == {}
        assert dependency_engine.get_topological_order() == []

    def test_single_node(self, dependency_engine):
        """
        Test: Edge case - single question with no dependencies
        
        Verifies handling of trivial graph with one node.
        """
        # Arrange
        single_question = [{"id": "ONLY", "ai_context_include_answers": []}]
        
        # Act
        dependency_engine.build_dependency_graph(single_question)
        
        # Assert
        graph = dependency_engine.get_dependency_graph()
        assert graph == {"ONLY": []}
        
        order = dependency_engine.get_topological_order()
        assert order == ["ONLY"]
        
        cascaded = dependency_engine.get_cascade_dependencies("ONLY")
        assert cascaded == []

    def test_complex_dependency_chains(self, dependency_engine):
        """
        Test: Edge case - complex multi-level dependency chains
        
        Tests deep, complex dependency structures to ensure scalability.
        """
        # Arrange: Create complex chain A->B->C->D->E and A->F->G->D
        complex_questions = [
            {"id": "A", "ai_context_include_answers": []},
            {"id": "B", "ai_context_include_answers": ["A"]},
            {"id": "C", "ai_context_include_answers": ["B"]},
            {"id": "D", "ai_context_include_answers": ["C", "G"]},  # Multiple inputs
            {"id": "E", "ai_context_include_answers": ["D"]},
            {"id": "F", "ai_context_include_answers": ["A"]},  # Parallel branch
            {"id": "G", "ai_context_include_answers": ["F"]}
        ]
        
        # Act
        dependency_engine.build_dependency_graph(complex_questions)
        
        # Assert: Topological order respects all constraints
        order = dependency_engine.get_topological_order()
        
        # A must be first
        assert order[0] == "A"
        
        # B and F must come after A
        a_pos = order.index("A")
        b_pos = order.index("B") 
        f_pos = order.index("F")
        assert a_pos < b_pos
        assert a_pos < f_pos
        
        # C must come after B, G must come after F
        c_pos = order.index("C")
        g_pos = order.index("G")
        assert b_pos < c_pos
        assert f_pos < g_pos
        
        # D must come after both C and G
        d_pos = order.index("D")
        assert c_pos < d_pos
        assert g_pos < d_pos
        
        # E must come after D
        e_pos = order.index("E")
        assert d_pos < e_pos

    def test_diamond_dependencies(self, dependency_engine, diamond_questions):
        """
        Test: Edge case - diamond dependency pattern
        
        Tests the classic diamond pattern where multiple paths lead to the same node.
        Pattern: Q1 -> {Q2, Q3} -> Q4
        """
        # Act
        dependency_engine.build_dependency_graph(diamond_questions)
        
        # Assert: Correct graph structure
        graph = dependency_engine.get_dependency_graph()
        
        assert graph["Q1"] == []
        assert "Q1" in graph["Q2"]
        assert "Q1" in graph["Q3"] 
        assert "Q2" in graph["Q4"]
        assert "Q3" in graph["Q4"]
        
        # Topological order should be valid
        order = dependency_engine.get_topological_order()
        
        q1_pos = order.index("Q1")
        q2_pos = order.index("Q2")
        q3_pos = order.index("Q3")
        q4_pos = order.index("Q4")
        
        assert q1_pos < q2_pos
        assert q1_pos < q3_pos
        assert q2_pos < q4_pos
        assert q3_pos < q4_pos
        
        # Cascade from Q1 should reach Q4 through both paths
        cascaded = dependency_engine.get_cascade_dependencies("Q1")
        assert "Q2" in cascaded
        assert "Q3" in cascaded 
        assert "Q4" in cascaded

    def test_forest_of_trees(self, dependency_engine, forest_questions):
        """
        Test: Edge case - forest of dependency trees
        
        Tests multiple independent dependency trees in the same graph.
        """
        # Act
        dependency_engine.build_dependency_graph(forest_questions)
        
        # Assert: All questions included
        graph = dependency_engine.get_dependency_graph()
        assert len(graph) == 6
        
        # Tree 1 structure: A -> B -> C
        assert graph["A"] == []
        assert "A" in graph["B"]
        assert "B" in graph["C"]
        
        # Tree 2 structure: X -> Y
        assert graph["X"] == []
        assert "X" in graph["Y"]
        
        # Isolated node
        assert graph["Z"] == []
        
        # Cascades should be independent
        cascade_a = dependency_engine.get_cascade_dependencies("A")
        cascade_x = dependency_engine.get_cascade_dependencies("X")
        cascade_z = dependency_engine.get_cascade_dependencies("Z")
        
        assert "B" in cascade_a
        assert "C" in cascade_a
        assert "X" not in cascade_a
        assert "Y" not in cascade_a
        assert "Z" not in cascade_a
        
        assert "Y" in cascade_x
        assert "A" not in cascade_x
        assert "B" not in cascade_x
        assert "C" not in cascade_x
        assert "Z" not in cascade_x
        
        assert len(cascade_z) == 0

    def test_self_dependency_detection(self, dependency_engine):
        """
        Test: Edge case - question depending on itself
        
        Self-dependencies should be detected as a special case of circular dependency.
        """
        # Arrange: Question that depends on itself
        self_dep_questions = [
            {"id": "SELF", "ai_context_include_answers": ["SELF"]}
        ]
        
        # Act & Assert: Should detect self-dependency
        with pytest.raises(ValueError) as exc_info:
            dependency_engine.build_dependency_graph(self_dep_questions)
            
        error_message = str(exc_info.value)
        assert "self-dependency" in error_message.lower() or "circular" in error_message.lower()
        assert "SELF" in error_message


class TestDependencyEngineIntegration:
    """
    Integration tests for Dependency Engine with real-world scenarios
    """
    
    @pytest.fixture
    def realistic_questions(self) -> List[Dict[str, Any]]:
        """
        Realistic question structure based on actual q4.toml patterns
        """
        return [
            {
                "id": "MET.LOC",
                "text": "Business location", 
                "ai_context_include_answers": []
            },
            {
                "id": "SG01",
                "text": "Why selling?",
                "ai_context_include_answers": []
            },
            {
                "id": "SG02", 
                "text": "Time on market",
                "ai_context_include_answers": ["SG01"]
            },
            {
                "id": "SG04",
                "text": "Revenue trend",
                "ai_context_include_answers": []
            },
            {
                "id": "SG05",
                "text": "Revenue consistency", 
                "ai_context_include_answers": ["SG04"]
            },
            {
                "id": "SG06",
                "text": "Working capital seasonality",
                "ai_context_include_answers": ["SG04"]
            },
            {
                "id": "SG07",
                "text": "Gross margins",
                "ai_context_include_answers": []
            },
            {
                "id": "SG08", 
                "text": "Discounting frequency",
                "ai_context_include_answers": ["SG07", "SG04"]
            }
        ]

    @pytest.fixture
    def dependency_engine(self):
        """Create DependencyEngine instance"""
        from src.backend.dependency_engine import DependencyEngine
        return DependencyEngine()

    def test_realistic_dependency_graph(self, dependency_engine, realistic_questions):
        """
        Test: Real-world question dependency patterns work correctly
        
        Based on actual patterns from q4.toml
        """
        # Act
        dependency_engine.build_dependency_graph(realistic_questions)
        
        # Assert: Correct dependency structure
        graph = dependency_engine.get_dependency_graph()
        
        # SG02 depends on SG01
        assert "SG01" in graph["SG02"]
        
        # SG05 and SG06 both depend on SG04
        assert "SG04" in graph["SG05"]
        assert "SG04" in graph["SG06"]
        
        # SG08 has multiple dependencies
        assert "SG07" in graph["SG08"]
        assert "SG04" in graph["SG08"]
        
        # Topological order is valid
        order = dependency_engine.get_topological_order()
        assert len(order) == 8
        
        # Verify specific ordering constraints
        sg01_pos = order.index("SG01")
        sg02_pos = order.index("SG02")
        sg04_pos = order.index("SG04")
        sg05_pos = order.index("SG05")
        sg06_pos = order.index("SG06")
        sg07_pos = order.index("SG07")
        sg08_pos = order.index("SG08")
        
        assert sg01_pos < sg02_pos
        assert sg04_pos < sg05_pos
        assert sg04_pos < sg06_pos
        assert sg07_pos < sg08_pos
        assert sg04_pos < sg08_pos

    def test_realistic_cascade_scenarios(self, dependency_engine, realistic_questions):
        """
        Test: Realistic cascade scenarios from business questionnaire
        """
        # Arrange
        dependency_engine.build_dependency_graph(realistic_questions)
        
        # Act & Assert: SG04 change cascades to dependent questions
        cascaded_sg04 = dependency_engine.get_cascade_dependencies("SG04")
        
        assert "SG05" in cascaded_sg04
        assert "SG06" in cascaded_sg04
        assert "SG08" in cascaded_sg04
        
        # SG01 only affects SG02
        cascaded_sg01 = dependency_engine.get_cascade_dependencies("SG01") 
        assert cascaded_sg01 == ["SG02"]
        
        # SG07 only affects SG08
        cascaded_sg07 = dependency_engine.get_cascade_dependencies("SG07")
        assert cascaded_sg07 == ["SG08"]

    def test_performance_with_large_graph(self, dependency_engine):
        """
        Test: Performance with larger dependency graphs
        
        Tests scalability with graphs approaching real-world size.
        """
        # Arrange: Generate large question set (simulate 50+ questions)
        large_questions = []
        
        # Create chains of dependencies
        for i in range(50):
            deps = []
            if i > 0:
                deps.append(f"Q{i-1}")  # Linear dependency
            if i > 5 and i % 5 == 0:
                deps.append(f"Q{i-5}")  # Additional cross-dependency
                
            large_questions.append({
                "id": f"Q{i}",
                "ai_context_include_answers": deps
            })
        
        # Act: Build large graph
        import time
        start_time = time.time()
        
        dependency_engine.build_dependency_graph(large_questions)
        order = dependency_engine.get_topological_order()
        
        end_time = time.time()
        
        # Assert: Performance is acceptable (should be sub-second)
        assert (end_time - start_time) < 1.0
        assert len(order) == 50
        
        # Verify correctness of large graph
        for i in range(1, 50):
            assert order.index(f"Q{i-1}") < order.index(f"Q{i}")


class TestDependencyEngineErrorHandling:
    """
    Error handling and edge case tests for Dependency Engine
    """
    
    @pytest.fixture  
    def dependency_engine(self):
        """Create DependencyEngine instance"""
        from src.backend.dependency_engine import DependencyEngine
        return DependencyEngine()

    def test_malformed_question_data(self, dependency_engine):
        """
        Test: Handles malformed question data gracefully
        """
        # Test missing required fields
        malformed_questions = [
            {"id": "Q1"},  # Missing ai_context_include_answers
            {"ai_context_include_answers": ["Q1"]},  # Missing id
            {"id": "Q3", "ai_context_include_answers": None}  # Null dependencies
        ]
        
        # Should not crash, should handle gracefully
        dependency_engine.build_dependency_graph(malformed_questions)
        
        # Valid questions should still be processed
        graph = dependency_engine.get_dependency_graph()
        assert "Q1" in graph
        assert "Q3" in graph

    def test_duplicate_question_ids(self, dependency_engine):
        """
        Test: Handles duplicate question IDs appropriately
        """
        # Arrange: Duplicate IDs
        duplicate_questions = [
            {"id": "DUPLICATE", "ai_context_include_answers": []},
            {"id": "DUPLICATE", "ai_context_include_answers": ["OTHER"]},
            {"id": "OTHER", "ai_context_include_answers": []}
        ]
        
        # Act: Should handle duplicates (last wins or merge strategy)
        dependency_engine.build_dependency_graph(duplicate_questions)
        
        # Assert: System remains stable
        graph = dependency_engine.get_dependency_graph()
        assert "DUPLICATE" in graph
        assert "OTHER" in graph

    def test_very_long_dependency_chains(self, dependency_engine):
        """
        Test: Handles very long dependency chains without stack overflow
        """
        # Arrange: Create chain of 1000+ dependencies
        long_chain = []
        for i in range(1000):
            deps = [f"Q{i-1}"] if i > 0 else []
            long_chain.append({
                "id": f"Q{i}",
                "ai_context_include_answers": deps
            })
        
        # Act: Should handle long chains
        dependency_engine.build_dependency_graph(long_chain)
        order = dependency_engine.get_topological_order()
        
        # Assert: Correct order maintained
        assert len(order) == 1000
        for i in range(1, 1000):
            assert order.index(f"Q{i-1}") < order.index(f"Q{i}")

    def test_empty_string_ids(self, dependency_engine):
        """
        Test: Handles empty or whitespace question IDs
        """
        # Arrange
        weird_id_questions = [
            {"id": "", "ai_context_include_answers": []},
            {"id": "   ", "ai_context_include_answers": []},
            {"id": "NORMAL", "ai_context_include_answers": ["", "   "]}
        ]
        
        # Act: Should handle gracefully without crashing
        dependency_engine.build_dependency_graph(weird_id_questions)
        
        # Assert: System remains stable
        graph = dependency_engine.get_dependency_graph()
        assert "NORMAL" in graph

    def test_unicode_question_ids(self, dependency_engine):
        """
        Test: Handles Unicode question IDs correctly
        """
        # Arrange: Unicode IDs
        unicode_questions = [
            {"id": "问题1", "ai_context_include_answers": []},
            {"id": "سؤال2", "ai_context_include_answers": ["问题1"]},
            {"id": "Вопрос3", "ai_context_include_answers": ["سؤال2"]}
        ]
        
        # Act
        dependency_engine.build_dependency_graph(unicode_questions)
        
        # Assert: Unicode handling works
        order = dependency_engine.get_topological_order()
        assert "问题1" in order
        assert "سؤال2" in order  
        assert "Вопрос3" in order
        
        # Verify correct dependency order
        assert order.index("问题1") < order.index("سؤال2")
        assert order.index("سؤال2") < order.index("Вопрос3")


# Test data fixtures for specific scenarios
@pytest.fixture
def complex_real_world_scenario():
    """
    Complex real-world scenario based on actual questionnaire patterns
    Tests the most complex dependency patterns found in q4.toml
    """
    return [
        # Basic info (no dependencies)
        {"id": "MET.LOC", "ai_context_include_answers": []},
        {"id": "MET.IND", "ai_context_include_answers": []},
        {"id": "MET.SIZE", "ai_context_include_answers": []},
        
        # Strategic (some interdependencies)  
        {"id": "SG01", "ai_context_include_answers": []},
        {"id": "SG02", "ai_context_include_answers": ["SG01"]},
        {"id": "SG04", "ai_context_include_answers": []},
        {"id": "SG05", "ai_context_include_answers": ["SG04"]},
        {"id": "SG06", "ai_context_include_answers": ["SG04"]},
        {"id": "SG08", "ai_context_include_answers": ["SG07", "SG04"]},
        {"id": "SG07", "ai_context_include_answers": []},
        
        # Operations (complex multi-dependencies)
        {"id": "SG09", "ai_context_include_answers": []},
        {"id": "SG10", "ai_context_include_answers": ["SG09"]}, 
        {"id": "SG11", "ai_context_include_answers": ["SG09", "SG10"]},
        {"id": "SG13", "ai_context_include_answers": ["SG04"]},
        {"id": "SG12", "ai_context_include_answers": ["SG04", "SG13"]},
        
        # Financial (highly interconnected)
        {"id": "SG14", "ai_context_include_answers": []},
        {"id": "SG15", "ai_context_include_answers": ["SG14"]},
        {"id": "SG16", "ai_context_include_answers": ["SG04"]},
        {"id": "SG17", "ai_context_include_answers": ["SG16", "SG04"]},
        
        # Management (owner dependency analysis)
        {"id": "SG26", "ai_context_include_answers": []},
        {"id": "SG27", "ai_context_include_answers": ["SG26"]},
        {"id": "SG28", "ai_context_include_answers": ["SG26", "SG27"]},
        {"id": "SG29", "ai_context_include_answers": ["SG28", "SG09", "SG10"]}
    ]


def test_complex_real_world_integration(complex_real_world_scenario):
    """
    Integration test with realistic complex dependency patterns
    
    This test uses patterns directly from the actual questionnaire
    to ensure the Dependency Engine can handle real-world complexity.
    """
    # This test will fail initially - that's expected in TDD Red phase
    from src.backend.dependency_engine import DependencyEngine
    
    engine = DependencyEngine()
    
    # Act: Build the complex graph
    engine.build_dependency_graph(complex_real_world_scenario)
    
    # Assert: All questions processed
    graph = engine.get_dependency_graph()
    assert len(graph) == len(complex_real_world_scenario)
    
    # Verify some key dependency patterns
    assert "SG01" in graph["SG02"]
    assert "SG04" in graph["SG05"] 
    assert "SG04" in graph["SG06"]
    assert "SG07" in graph["SG08"]
    assert "SG04" in graph["SG08"]
    assert "SG09" in graph["SG10"]
    assert "SG09" in graph["SG11"]
    assert "SG10" in graph["SG11"] 
    
    # Verify complex multi-dependency scenarios
    assert "SG28" in graph["SG29"]
    assert "SG09" in graph["SG29"] 
    assert "SG10" in graph["SG29"]
    
    # Get topological order and verify it's valid
    order = engine.get_topological_order()
    assert len(order) == len(complex_real_world_scenario)
    
    # Spot check some critical ordering requirements
    sg01_pos = order.index("SG01")
    sg02_pos = order.index("SG02")
    assert sg01_pos < sg02_pos
    
    sg04_pos = order.index("SG04")
    sg05_pos = order.index("SG05")
    sg06_pos = order.index("SG06")
    assert sg04_pos < sg05_pos
    assert sg04_pos < sg06_pos
    
    # Test cascade scenarios
    cascaded_sg04 = engine.get_cascade_dependencies("SG04")
    expected_sg04_cascades = ["SG05", "SG06", "SG08", "SG13", "SG12", "SG16", "SG17"]
    for expected in expected_sg04_cascades:
        assert expected in cascaded_sg04
    
    cascaded_sg09 = engine.get_cascade_dependencies("SG09")
    expected_sg09_cascades = ["SG10", "SG11", "SG29"]
    for expected in expected_sg09_cascades:
        assert expected in cascaded_sg09


if __name__ == "__main__":
    """
    Run tests directly for development
    These tests will FAIL initially until DependencyEngine is implemented
    """
    pytest.main([__file__, "-v", "--tb=short"])