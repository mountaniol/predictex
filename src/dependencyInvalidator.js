/**
 * @file Dependency invalidation system for QnA Evaluator
 * @summary Manages cascading invalidation when question answers change
 * @version 1.0.0
 * @author Predictex AI
 */

/**
 * Build reverse dependency graph for efficient invalidation lookups
 * @param {Array} sections - All question sections
 * @returns {Map} Map from question ID to array of dependent question IDs
 */
export const buildReverseDependencyGraph = (sections) => {
  const reverseDeps = new Map();
  
  if (!sections || !Array.isArray(sections)) {
    return reverseDeps;
  }
  
  // Initialize map with empty arrays for all questions
  sections.forEach(section => {
    if (section.questions && Array.isArray(section.questions)) {
      section.questions.forEach(question => {
        if (question.id) {
          reverseDeps.set(question.id, []);
        }
      });
    }
  });
  
  // Build reverse dependencies
  sections.forEach(section => {
    if (section.questions && Array.isArray(section.questions)) {
      section.questions.forEach(question => {
        const dependencies = question.ai_context?.include_answers || [];
        
        dependencies.forEach(depId => {
          if (reverseDeps.has(depId)) {
            reverseDeps.get(depId).push(question.id);
          } else {
            // Dependency points to non-existent question
            console.warn(`[DependencyInvalidator] Question ${question.id} depends on non-existent question: ${depId}`);
            reverseDeps.set(depId, [question.id]);
          }
        });
      });
    }
  });
  
  return reverseDeps;
};

/**
 * Find all questions that should be invalidated when a question changes
 * @param {string} changedQuestionId - ID of the question that changed
 * @param {Map} reverseDependencyGraph - Reverse dependency graph
 * @param {number} maxDepth - Maximum recursion depth to prevent infinite loops
 * @returns {Set} Set of question IDs that should be invalidated
 */
export const findInvalidationTargets = (changedQuestionId, reverseDependencyGraph, maxDepth = 10) => {
  const toInvalidate = new Set();
  const visited = new Set();
  
  const traverse = (questionId, depth = 0) => {
    if (depth > maxDepth) {
      console.warn(`[DependencyInvalidator] Max recursion depth reached for question: ${questionId}`);
      return;
    }
    
    if (visited.has(questionId)) {
      // Circular dependency detected
      console.warn(`[DependencyInvalidator] Circular dependency detected involving: ${questionId}`);
      return;
    }
    
    visited.add(questionId);
    
    const dependents = reverseDependencyGraph.get(questionId) || [];
    dependents.forEach(dependentId => {
      toInvalidate.add(dependentId);
      // Recursively invalidate questions that depend on this dependent
      traverse(dependentId, depth + 1);
    });
    
    visited.delete(questionId);
  };
  
  traverse(changedQuestionId);
  
  return toInvalidate;
};

/**
 * Create a dependency invalidation manager
 * @param {Array} sections - Question sections
 * @param {Object} options - Configuration options
 * @returns {Object} Dependency invalidation manager
 */
export const createDependencyInvalidator = (sections, options = {}) => {
  const {
    maxInvalidationDepth = 10,
    logInvalidations = true,
    preventCircularInvalidation = true,
    onInvalidation = (questionIds) => {
      if (logInvalidations && questionIds.length > 0) {
        console.log(`[DependencyInvalidator] Invalidating ${questionIds.length} dependent questions:`, questionIds);
      }
    }
  } = options;
  
  let reverseDependencyGraph = buildReverseDependencyGraph(sections);
  
  const manager = {
    /**
     * Update the dependency graph when sections change
     * @param {Array} newSections - Updated sections
     */
    updateSections: (newSections) => {
      reverseDependencyGraph = buildReverseDependencyGraph(newSections);
      
      if (logInvalidations) {
        const totalQuestions = reverseDependencyGraph.size;
        const questionsWithDependents = Array.from(reverseDependencyGraph.values()).filter(deps => deps.length > 0).length;
        console.log(`[DependencyInvalidator] Updated dependency graph: ${totalQuestions} questions, ${questionsWithDependents} have dependents`);
      }
    },
    
    /**
     * Find questions that should be invalidated when a question changes
     * @param {string} changedQuestionId - ID of changed question
     * @returns {Array} Array of question IDs to invalidate
     */
    getInvalidationTargets: (changedQuestionId) => {
      const targets = findInvalidationTargets(
        changedQuestionId, 
        reverseDependencyGraph, 
        maxInvalidationDepth
      );
      
      const targetArray = Array.from(targets);
      onInvalidation(targetArray);
      
      return targetArray;
    },
    
    /**
     * Get all questions that depend on a specific question
     * @param {string} questionId - Question ID to check
     * @returns {Array} Direct dependents (not recursive)
     */
    getDirectDependents: (questionId) => {
      return reverseDependencyGraph.get(questionId) || [];
    },
    
    /**
     * Check if a question has any dependents
     * @param {string} questionId - Question ID to check
     * @returns {boolean} Whether question has dependents
     */
    hasDependents: (questionId) => {
      const dependents = reverseDependencyGraph.get(questionId) || [];
      return dependents.length > 0;
    },
    
    /**
     * Get statistics about the dependency graph
     * @returns {Object} Dependency statistics
     */
    getStats: () => {
      const allDependencies = Array.from(reverseDependencyGraph.values());
      const totalQuestions = reverseDependencyGraph.size;
      const questionsWithDependents = allDependencies.filter(deps => deps.length > 0).length;
      const totalDependencies = allDependencies.reduce((sum, deps) => sum + deps.length, 0);
      const maxDependents = Math.max(0, ...allDependencies.map(deps => deps.length));
      
      return {
        totalQuestions,
        questionsWithDependents,
        totalDependencies,
        maxDependents,
        averageDependents: totalQuestions > 0 ? totalDependencies / totalQuestions : 0,
        dependencyDensity: totalQuestions > 0 ? totalDependencies / (totalQuestions * totalQuestions) : 0
      };
    },
    
    /**
     * Validate the dependency graph for potential issues
     * @returns {Object} Validation results
     */
    validateGraph: () => {
      const issues = [];
      const warnings = [];
      
      // Check for potential circular dependencies
      const visited = new Set();
      const recursionStack = new Set();
      
      const hasCycle = (questionId) => {
        if (recursionStack.has(questionId)) {
          return true; // Cycle detected
        }
        
        if (visited.has(questionId)) {
          return false; // Already processed
        }
        
        visited.add(questionId);
        recursionStack.add(questionId);
        
        const dependents = reverseDependencyGraph.get(questionId) || [];
        for (const dependentId of dependents) {
          if (hasCycle(dependentId)) {
            return true;
          }
        }
        
        recursionStack.delete(questionId);
        return false;
      };
      
      // Check all questions for cycles
      for (const questionId of reverseDependencyGraph.keys()) {
        if (!visited.has(questionId) && hasCycle(questionId)) {
          issues.push(`Circular dependency detected involving question: ${questionId}`);
        }
      }
      
      // Check for questions with many dependents (potential performance issue)
      for (const [questionId, dependents] of reverseDependencyGraph.entries()) {
        if (dependents.length > 20) {
          warnings.push(`Question ${questionId} has ${dependents.length} dependents (may impact performance)`);
        }
      }
      
      // Check for orphaned references
      const allQuestionIds = new Set(reverseDependencyGraph.keys());
      const referencedIds = new Set();
      
      for (const dependents of reverseDependencyGraph.values()) {
        dependents.forEach(id => referencedIds.add(id));
      }
      
      for (const referencedId of referencedIds) {
        if (!allQuestionIds.has(referencedId)) {
          warnings.push(`Referenced question ${referencedId} does not exist`);
        }
      }
      
      return {
        isValid: issues.length === 0,
        issues,
        warnings,
        summary: {
          circularDependencies: issues.filter(i => i.includes('Circular')).length,
          performanceWarnings: warnings.filter(w => w.includes('performance')).length,
          orphanedReferences: warnings.filter(w => w.includes('does not exist')).length
        }
      };
    },
    
    /**
     * Get the current reverse dependency graph
     * @returns {Map} Current reverse dependency graph
     */
    getGraph: () => {
      return new Map(reverseDependencyGraph); // Return a copy
    }
  };
  
  return manager;
};

/**
 * Helper function to create invalidation handler for React components
 * @param {Object} dependencyInvalidator - Dependency invalidator instance
 * @param {Object} atomicState - Atomic state manager
 * @returns {Function} Invalidation handler function
 */
export const createInvalidationHandler = (dependencyInvalidator, atomicState) => {
  return (changedQuestionId, reason = 'answer-change') => {
    const targetsToInvalidate = dependencyInvalidator.getInvalidationTargets(changedQuestionId);
    
    if (targetsToInvalidate.length > 0) {
      console.log(`[DependencyInvalidator] Invalidating ${targetsToInvalidate.length} questions due to ${reason} in ${changedQuestionId}`);
      
      // Clear scores and explanations for invalidated questions
      const clearData = {};
      targetsToInvalidate.forEach(questionId => {
        clearData[questionId] = undefined; // This will clear the score/explanation
      });
      
      // Use atomic state manager to clear invalidated data
      atomicState.updateAtomic({
        scores: clearData,
        explanations: clearData
      });
      
      return targetsToInvalidate;
    }
    
    return [];
  };
};

export default {
  buildReverseDependencyGraph,
  findInvalidationTargets,
  createDependencyInvalidator,
  createInvalidationHandler
};