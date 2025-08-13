/**
 * @file Dependency validation utilities for QnA Evaluator
 * @summary Provides functions to validate question dependency graphs at load time
 * to prevent circular dependencies and ensure DAG properties.
 * @version 1.0.0
 * @author Predictex AI
 */

/**
 * Validates that the question dependency graph is a valid DAG (Directed Acyclic Graph)
 * @param {Array} questions - Array of question objects from q4.json
 * @returns {Object} Validation result with isValid boolean and error details
 */
export const validateDependencyGraph = (questions) => {
  const result = {
    isValid: true,
    errors: [],
    warnings: [],
    stats: {
      totalQuestions: questions.length,
      questionsWithDeps: 0,
      maxDepthFound: 0,
      forwardReferences: 0,
      circularDependencies: [],
      missingReferences: []
    }
  };

  // Build question ID map and dependency graph
  const questionMap = new Map();
  const dependencies = new Map();
  const questionPositions = new Map();
  
  // Initialize maps
  questions.forEach((q, index) => {
    if (q.question_type === 'internal') return; // Skip internal questions
    
    questionMap.set(q.id, q);
    questionPositions.set(q.id, index);
    
    const deps = q.ai_context?.include_answers || [];
    if (deps.length > 0 && !deps.includes('all')) {
      dependencies.set(q.id, deps);
      result.stats.questionsWithDeps++;
    } else {
      dependencies.set(q.id, []);
    }
  });

  // Check for missing references
  for (const [questionId, deps] of dependencies) {
    for (const depId of deps) {
      if (depId === 'all') continue;
      
      if (!questionMap.has(depId)) {
        result.errors.push(`Question ${questionId} depends on non-existent question: ${depId}`);
        result.stats.missingReferences.push({ from: questionId, to: depId });
        result.isValid = false;
      }
    }
  }

  // Check for forward references (dependencies on questions defined later)
  for (const [questionId, deps] of dependencies) {
    const questionPos = questionPositions.get(questionId);
    
    for (const depId of deps) {
      if (depId === 'all') continue;
      
      const depPos = questionPositions.get(depId);
      if (depPos !== undefined && depPos > questionPos) {
        result.warnings.push(`Question ${questionId} (pos ${questionPos}) depends on ${depId} (pos ${depPos}) - forward reference`);
        result.stats.forwardReferences++;
      }
    }
  }

  // Detect cycles using DFS
  const visited = new Set();
  const recursionStack = new Set();
  const pathStack = [];

  const hasCycleDFS = (nodeId, currentPath) => {
    if (recursionStack.has(nodeId)) {
      // Found a cycle
      const cycleStart = currentPath.indexOf(nodeId);
      const cycle = currentPath.slice(cycleStart).concat([nodeId]);
      result.errors.push(`Circular dependency detected: ${cycle.join(' -> ')}`);
      result.stats.circularDependencies.push(cycle);
      result.isValid = false;
      return true;
    }

    if (visited.has(nodeId)) {
      return false; // Already processed this subtree
    }

    visited.add(nodeId);
    recursionStack.add(nodeId);
    currentPath.push(nodeId);

    const deps = dependencies.get(nodeId) || [];
    for (const depId of deps) {
      if (depId === 'all') continue;
      
      if (questionMap.has(depId) && hasCycleDFS(depId, [...currentPath])) {
        return true;
      }
    }

    recursionStack.delete(nodeId);
    currentPath.pop();
    return false;
  };

  // Check all questions for cycles
  for (const questionId of questionMap.keys()) {
    if (!visited.has(questionId)) {
      hasCycleDFS(questionId, []);
    }
  }

  // Calculate maximum dependency depth
  const depthCache = new Map();
  
  const calculateDepth = (nodeId, visiting = new Set()) => {
    if (visiting.has(nodeId)) {
      return 0; // Prevent infinite recursion in case of cycles
    }
    
    if (depthCache.has(nodeId)) {
      return depthCache.get(nodeId);
    }

    visiting.add(nodeId);
    const deps = dependencies.get(nodeId) || [];
    let maxDepth = 0;

    for (const depId of deps) {
      if (depId === 'all') continue;
      
      if (questionMap.has(depId)) {
        const depDepth = calculateDepth(depId, visiting);
        maxDepth = Math.max(maxDepth, depDepth + 1);
      }
    }

    visiting.delete(nodeId);
    depthCache.set(nodeId, maxDepth);
    return maxDepth;
  };

  for (const questionId of questionMap.keys()) {
    const depth = calculateDepth(questionId);
    result.stats.maxDepthFound = Math.max(result.stats.maxDepthFound, depth);
  }

  return result;
};

/**
 * Performs topological sort on the dependency graph
 * @param {Array} questions - Array of question objects
 * @returns {Object} Result with sorted order and validity
 */
export const topologicalSort = (questions) => {
  const questionIds = questions
    .filter(q => q.question_type !== 'internal')
    .map(q => q.id);
    
  const dependencies = new Map();
  const inDegree = new Map();
  const graph = new Map();

  // Initialize
  questionIds.forEach(id => {
    dependencies.set(id, []);
    inDegree.set(id, 0);
    graph.set(id, []);
  });

  // Build dependency graph
  questions.forEach(q => {
    if (q.question_type === 'internal') return;
    
    const deps = q.ai_context?.include_answers || [];
    if (deps.length > 0 && !deps.includes('all')) {
      dependencies.set(q.id, deps);
      
      deps.forEach(depId => {
        if (depId !== 'all' && graph.has(depId)) {
          graph.get(depId).push(q.id);
          inDegree.set(q.id, inDegree.get(q.id) + 1);
        }
      });
    }
  });

  // Kahn's algorithm
  const queue = [];
  const result = [];

  // Find nodes with no incoming edges
  for (const [nodeId, degree] of inDegree) {
    if (degree === 0) {
      queue.push(nodeId);
    }
  }

  while (queue.length > 0) {
    const nodeId = queue.shift();
    result.push(nodeId);

    const neighbors = graph.get(nodeId) || [];
    neighbors.forEach(neighborId => {
      inDegree.set(neighborId, inDegree.get(neighborId) - 1);
      if (inDegree.get(neighborId) === 0) {
        queue.push(neighborId);
      }
    });
  }

  return {
    isValid: result.length === questionIds.length,
    sortedOrder: result,
    totalQuestions: questionIds.length,
    processedQuestions: result.length
  };
};

/**
 * Creates a comprehensive dependency report
 * @param {Array} questions - Array of question objects
 * @returns {Object} Detailed report of dependency analysis
 */
export const createDependencyReport = (questions) => {
  const validation = validateDependencyGraph(questions);
  const topoSort = topologicalSort(questions);
  
  return {
    timestamp: new Date().toISOString(),
    validation,
    topologicalSort: topoSort,
    recommendations: generateRecommendations(validation, topoSort)
  };
};

/**
 * Generates recommendations based on validation results
 * @param {Object} validation - Validation result
 * @param {Object} topoSort - Topological sort result
 * @returns {Array} Array of recommendation strings
 */
const generateRecommendations = (validation, topoSort) => {
  const recommendations = [];

  if (!validation.isValid) {
    recommendations.push('❌ CRITICAL: Fix circular dependencies before deployment');
    
    if (validation.stats.missingReferences.length > 0) {
      recommendations.push('❌ CRITICAL: Fix missing question references');
    }
  }

  if (validation.stats.forwardReferences > 0) {
    recommendations.push('⚠️ WARNING: Consider reordering questions to avoid forward references');
  }

  if (validation.stats.maxDepthFound > 5) {
    recommendations.push(`⚠️ WARNING: Deep dependency chain detected (depth: ${validation.stats.maxDepthFound}). Consider simplifying.`);
  }

  if (!topoSort.isValid) {
    recommendations.push('❌ CRITICAL: Topological sort failed - indicates circular dependencies');
  }

  if (validation.isValid && topoSort.isValid) {
    recommendations.push('✅ Dependency graph is valid and ready for use');
  }

  return recommendations;
};

export default {
  validateDependencyGraph,
  topologicalSort,
  createDependencyReport
};