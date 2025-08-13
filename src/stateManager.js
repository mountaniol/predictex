/**
 * @file State management utilities for atomic updates
 * @summary Provides utilities for batched, atomic state updates to prevent
 * intermediate renders with inconsistent state.
 * @version 1.0.0
 * @author Predictex AI
 */

import { unstable_batchedUpdates } from 'react-dom';

/**
 * Creates a batched state updater that ensures all state updates happen atomically
 * @param {Object} setters - Object mapping state names to their setter functions
 * @returns {Function} Batched update function
 */
export const createBatchedStateUpdater = (setters) => {
  return (updates) => {
    unstable_batchedUpdates(() => {
      Object.entries(updates).forEach(([key, update]) => {
        const setter = setters[key];
        if (setter) {
          if (typeof update === 'function') {
            setter(update);
          } else {
            setter(update);
          }
        } else {
          console.warn(`[stateManager] No setter found for key: ${key}`);
        }
      });
    });
  };
};

/**
 * Creates an enhanced state manager with atomic update capabilities
 * @param {Object} initialState - Initial state values
 * @param {Object} setters - State setter functions
 * @returns {Object} Enhanced state manager with atomic operations
 */
export const createAtomicStateManager = (initialState, setters) => {
  const batchedUpdate = createBatchedStateUpdater(setters);
  
  return {
    /**
     * Atomically update multiple state values
     * @param {Object} updates - Object with state updates
     */
    updateAtomic: (updates) => {
      console.log('[stateManager] Atomic update:', Object.keys(updates));
      batchedUpdate(updates);
    },
    
    /**
     * Update with transformation functions for complex state logic
     * @param {Object} transformers - Object mapping state keys to transform functions
     */
    updateWithTransformers: (transformers) => {
      const updates = {};
      
      Object.entries(transformers).forEach(([key, transformer]) => {
        if (typeof transformer === 'function') {
          updates[key] = transformer;
        } else {
          updates[key] = () => transformer;
        }
      });
      
      batchedUpdate(updates);
    },
    
    /**
     * Clear specific state values atomically
     * @param {Array} stateKeys - Array of state keys to clear
     * @param {Object} clearValues - Optional custom clear values
     */
    clearAtomic: (stateKeys, clearValues = {}) => {
      const updates = {};
      
      stateKeys.forEach(key => {
        if (clearValues[key] !== undefined) {
          updates[key] = clearValues[key];
        } else {
          // Default clear values based on initial state type
          const initialValue = initialState[key];
          if (Array.isArray(initialValue)) {
            updates[key] = [];
          } else if (typeof initialValue === 'object' && initialValue !== null) {
            updates[key] = {};
          } else {
            updates[key] = null;
          }
        }
      });
      
      batchedUpdate(updates);
    }
  };
};

/**
 * Utility to merge state updates with conflict resolution
 * @param {Object} currentState - Current state values
 * @param {Object} updates - New updates to apply
 * @param {Object} options - Merge options
 * @returns {Object} Merged state updates
 */
export const mergeStateUpdates = (currentState, updates, options = {}) => {
  const { deepMerge = false, conflictResolver = null } = options;
  const merged = {};
  
  Object.entries(updates).forEach(([key, newValue]) => {
    const currentValue = currentState[key];
    
    if (conflictResolver && currentValue !== undefined) {
      merged[key] = conflictResolver(currentValue, newValue, key);
    } else if (deepMerge && typeof currentValue === 'object' && typeof newValue === 'object') {
      merged[key] = { ...currentValue, ...newValue };
    } else {
      merged[key] = newValue;
    }
  });
  
  return merged;
};

/**
 * React Hook for atomic state management
 * @param {Object} stateSetters - Object mapping state names to setter functions
 * @param {Object} initialState - Initial state for reference
 * @returns {Object} Atomic state manager functions
 */
export const useAtomicState = (stateSetters, initialState = {}) => {
  const atomicManager = createAtomicStateManager(initialState, stateSetters);
  
  return {
    updateAtomic: atomicManager.updateAtomic,
    updateWithTransformers: atomicManager.updateWithTransformers,
    clearAtomic: atomicManager.clearAtomic,
    
    /**
     * Specialized function for question evaluation state updates
     * @param {Object} evaluationResults - Results from AI evaluation
     */
    updateEvaluationResults: (evaluationResults) => {
      const {
        scores: newScores = {},
        explanations: newExplanations = {},
        questionStates: newStates = {}
      } = evaluationResults;
      
      atomicManager.updateWithTransformers({
        scores: (prev) => ({ ...prev, ...newScores }),
        explanations: (prev) => ({ ...prev, ...newExplanations }),
        questionStates: (prev) => ({ ...prev, ...newStates })
      });
    },
    
    /**
     * Clear question evaluation data atomically
     * @param {string} questionId - Question ID to clear
     */
    clearQuestionData: (questionId) => {
      atomicManager.updateWithTransformers({
        scores: (prev) => {
          const newScores = { ...prev };
          delete newScores[questionId];
          return newScores;
        },
        explanations: (prev) => {
          const newExplanations = { ...prev };
          delete newExplanations[questionId];
          return newExplanations;
        },
        questionStates: (prev) => ({ ...prev, [questionId]: 'unanswered' })
      });
    }
  };
};

export default {
  createBatchedStateUpdater,
  createAtomicStateManager,
  mergeStateUpdates,
  useAtomicState
};