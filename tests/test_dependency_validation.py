#!/usr/bin/env python3
"""
Test dependency validation with various edge cases and cycle scenarios.
Tests the theoretical validation designed in Task 2.3-2.4.
"""

import json
import os
import tempfile

def create_test_questions_with_cycle():
    """Create test questions with circular dependency A -> B -> C -> A"""
    return {
        "version": "test",
        "settings": {"labels": {}},
        "questions": [
            {
                "id": "A",
                "text": "Question A",
                "cluster_name": "Test",
                "position_in_cluster": 1,
                "question_type": "text",
                "ai_context": {"include_answers": ["C"]}  # A depends on C
            },
            {
                "id": "B", 
                "text": "Question B",
                "cluster_name": "Test",
                "position_in_cluster": 2,
                "question_type": "text",
                "ai_context": {"include_answers": ["A"]}  # B depends on A
            },
            {
                "id": "C",
                "text": "Question C", 
                "cluster_name": "Test",
                "position_in_cluster": 3,
                "question_type": "text",
                "ai_context": {"include_answers": ["B"]}  # C depends on B
            }
        ]
    }

def create_test_questions_with_forward_ref():
    """Create test questions with forward reference dependency"""
    return {
        "version": "test", 
        "settings": {"labels": {}},
        "questions": [
            {
                "id": "EARLY",
                "text": "Early Question",
                "cluster_name": "Test",
                "position_in_cluster": 1,
                "question_type": "text",
                "ai_context": {"include_answers": ["LATE"]}  # Forward reference
            },
            {
                "id": "LATE",
                "text": "Late Question",
                "cluster_name": "Test", 
                "position_in_cluster": 2,
                "question_type": "text",
                "ai_context": {"include_answers": []}
            }
        ]
    }

def create_test_questions_with_missing_refs():
    """Create test questions with missing reference dependencies"""
    return {
        "version": "test",
        "settings": {"labels": {}},
        "questions": [
            {
                "id": "EXISTING",
                "text": "Existing Question", 
                "cluster_name": "Test",
                "position_in_cluster": 1,
                "question_type": "text",
                "ai_context": {"include_answers": ["MISSING", "ALSO_MISSING"]}
            }
        ]
    }

def create_test_questions_valid_dag():
    """Create valid DAG structure for comparison"""
    return {
        "version": "test",
        "settings": {"labels": {}},
        "questions": [
            {
                "id": "ROOT1",
                "text": "Root Question 1",
                "cluster_name": "Test",
                "position_in_cluster": 1, 
                "question_type": "text",
                "ai_context": {"include_answers": []}
            },
            {
                "id": "ROOT2",
                "text": "Root Question 2",
                "cluster_name": "Test",
                "position_in_cluster": 2,
                "question_type": "text", 
                "ai_context": {"include_answers": []}
            },
            {
                "id": "CHILD1",
                "text": "Child Question 1",
                "cluster_name": "Test",
                "position_in_cluster": 3,
                "question_type": "text",
                "ai_context": {"include_answers": ["ROOT1"]}
            },
            {
                "id": "CHILD2", 
                "text": "Child Question 2",
                "cluster_name": "Test",
                "position_in_cluster": 4,
                "question_type": "text",
                "ai_context": {"include_answers": ["ROOT1", "ROOT2"]}
            },
            {
                "id": "GRANDCHILD",
                "text": "Grandchild Question",
                "cluster_name": "Test",
                "position_in_cluster": 5,
                "question_type": "text",
                "ai_context": {"include_answers": ["CHILD1", "CHILD2"]}
            }
        ]
    }

def run_js_validation(test_data):
    """Run JavaScript dependency validation on test data"""
    import subprocess
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        js_code = f"""
        import {{ createDependencyReport }} from './src/dependencyValidator.js';
        import fs from 'fs';
        
        const data = JSON.parse(fs.readFileSync('{temp_file}', 'utf8'));
        const report = createDependencyReport(data.questions);
        console.log(JSON.stringify(report, null, 2));
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mjs', delete=False) as js_f:
            js_f.write(js_code)
            js_file = js_f.name
        
        result = subprocess.run(
            ['node', js_file],
            capture_output=True,
            text=True,
            cwd='/media/AI/predictex/qna-evaluator'
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"JS validation error: {result.stderr}")
            return None
            
    finally:
        os.unlink(temp_file)
        os.unlink(js_file)

def test_circular_dependency_detection():
    """Test detection of circular dependencies"""
    print("🧪 Testing circular dependency detection...")
    
    test_data = create_test_questions_with_cycle()
    report = run_js_validation(test_data)
    
    if report:
        validation = report['validation']
        
        print(f"   Valid: {validation['isValid']}")
        print(f"   Errors: {len(validation['errors'])}")
        print(f"   Circular dependencies: {len(validation['stats']['circularDependencies'])}")
        
        if not validation['isValid'] and len(validation['stats']['circularDependencies']) > 0:
            print("   ✅ PASS: Circular dependency correctly detected")
            for error in validation['errors']:
                print(f"      {error}")
            return True
        else:
            print("   ❌ FAIL: Circular dependency not detected")
            return False
    else:
        print("   ❌ FAIL: Could not run validation")
        return False

def test_forward_reference_detection():
    """Test detection of forward references"""
    print("\\n🧪 Testing forward reference detection...")
    
    test_data = create_test_questions_with_forward_ref()
    report = run_js_validation(test_data)
    
    if report:
        validation = report['validation']
        
        print(f"   Valid: {validation['isValid']}")
        print(f"   Warnings: {len(validation['warnings'])}")
        print(f"   Forward references: {validation['stats']['forwardReferences']}")
        
        if validation['stats']['forwardReferences'] > 0:
            print("   ✅ PASS: Forward reference correctly detected")
            for warning in validation['warnings']:
                print(f"      {warning}")
            return True
        else:
            print("   ❌ FAIL: Forward reference not detected")
            return False
    else:
        print("   ❌ FAIL: Could not run validation")
        return False

def test_missing_reference_detection():
    """Test detection of missing references"""
    print("\\n🧪 Testing missing reference detection...")
    
    test_data = create_test_questions_with_missing_refs()
    report = run_js_validation(test_data)
    
    if report:
        validation = report['validation']
        
        print(f"   Valid: {validation['isValid']}")
        print(f"   Errors: {len(validation['errors'])}")
        print(f"   Missing references: {len(validation['stats']['missingReferences'])}")
        
        if not validation['isValid'] and len(validation['stats']['missingReferences']) > 0:
            print("   ✅ PASS: Missing references correctly detected")
            for error in validation['errors']:
                print(f"      {error}")
            return True
        else:
            print("   ❌ FAIL: Missing references not detected")
            return False
    else:
        print("   ❌ FAIL: Could not run validation")
        return False

def test_valid_dag_acceptance():
    """Test acceptance of valid DAG structure"""
    print("\\n🧪 Testing valid DAG acceptance...")
    
    test_data = create_test_questions_valid_dag()
    report = run_js_validation(test_data)
    
    if report:
        validation = report['validation']
        topo_sort = report['topologicalSort']
        
        print(f"   Valid: {validation['isValid']}")
        print(f"   Errors: {len(validation['errors'])}")
        print(f"   Topo sort valid: {topo_sort['isValid']}")
        print(f"   Max depth: {validation['stats']['maxDepthFound']}")
        
        if validation['isValid'] and topo_sort['isValid']:
            print("   ✅ PASS: Valid DAG correctly accepted")
            print(f"      Topological order: {' -> '.join(topo_sort['sortedOrder'])}")
            return True
        else:
            print("   ❌ FAIL: Valid DAG incorrectly rejected")
            return False
    else:
        print("   ❌ FAIL: Could not run validation")
        return False

def test_real_q4_validation():
    """Test validation on real q4.json file"""
    print("\\n🧪 Testing real q4.json validation...")
    
    try:
        with open('/media/AI/predictex/qna-evaluator/public/questions/q4.json', 'r') as f:
            test_data = json.load(f)
        
        report = run_js_validation(test_data)
        
        if report:
            validation = report['validation']
            topo_sort = report['topologicalSort']
            
            print(f"   Valid: {validation['isValid']}")
            print(f"   Total questions: {validation['stats']['totalQuestions']}")
            print(f"   Questions with deps: {validation['stats']['questionsWithDeps']}")
            print(f"   Max depth: {validation['stats']['maxDepthFound']}")
            print(f"   Forward references: {validation['stats']['forwardReferences']}")
            print(f"   Topo sort valid: {topo_sort['isValid']}")
            
            if validation['isValid'] and topo_sort['isValid']:
                print("   ✅ PASS: Real q4.json is valid")
                return True
            else:
                print("   ❌ FAIL: Real q4.json has issues")
                for error in validation['errors']:
                    print(f"      ERROR: {error}")
                return False
        else:
            print("   ❌ FAIL: Could not run validation")
            return False
            
    except Exception as e:
        print(f"   ❌ FAIL: Exception occurred: {e}")
        return False

def main():
    """Run all dependency validation tests"""
    print("=== DEPENDENCY VALIDATION TESTS ===")
    
    tests = [
        test_circular_dependency_detection,
        test_forward_reference_detection, 
        test_missing_reference_detection,
        test_valid_dag_acceptance,
        test_real_q4_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\\n=== RESULTS ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        return False

if __name__ == "__main__":
    main()