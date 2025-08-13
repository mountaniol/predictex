/**
 * @file Evaluation progress flag management utilities
 * @summary Centralized management of evaluation progress flags to prevent
 * race conditions and stuck evaluations.
 * @version 1.0.0
 * @author Predictex AI
 */

/**
 * Creates a managed evaluation progress tracker
 * @param {Object} options - Configuration options
 * @returns {Object} Evaluation progress manager
 */
export const createEvaluationProgressManager = (options = {}) => {
  const {
    timeoutMs = 30000, // 30 second timeout for stuck evaluations
    maxConcurrentEvaluations = 5,
    onTimeout = (questionId) => console.warn(`[EvaluationProgress] Timeout for question: ${questionId}`),
    onMaxConcurrent = () => console.warn(`[EvaluationProgress] Maximum concurrent evaluations reached`)
  } = options;

  const progressFlags = new Map();
  const timeouts = new Map();
  
  const manager = {
    /**
     * Check if evaluation is in progress for a question
     * @param {string} questionId - Question ID to check
     * @returns {boolean} Whether evaluation is in progress
     */
    isInProgress: (questionId) => {
      return progressFlags.has(questionId);
    },

    /**
     * Start evaluation for a question
     * @param {string} questionId - Question ID
     * @returns {boolean} Whether evaluation was started (false if already in progress or max concurrent reached)
     */
    startEvaluation: (questionId) => {
      // Check if already in progress
      if (progressFlags.has(questionId)) {
        console.log(`[EvaluationProgress] Already in progress: ${questionId}`);
        return false;
      }

      // Check concurrent limit
      if (progressFlags.size >= maxConcurrentEvaluations) {
        onMaxConcurrent();
        return false;
      }

      // Start evaluation
      const startTime = Date.now();
      progressFlags.set(questionId, { startTime, status: 'evaluating' });
      
      // Set timeout
      const timeoutId = setTimeout(() => {
        onTimeout(questionId);
        manager.forceComplete(questionId, 'timeout');
      }, timeoutMs);
      
      timeouts.set(questionId, timeoutId);
      
      console.log(`[EvaluationProgress] Started: ${questionId}`);
      return true;
    },

    /**
     * Complete evaluation for a question
     * @param {string} questionId - Question ID
     * @param {string} reason - Reason for completion (success, error, etc.)
     */
    completeEvaluation: (questionId, reason = 'success') => {
      if (!progressFlags.has(questionId)) {
        console.warn(`[EvaluationProgress] Trying to complete non-existent evaluation: ${questionId}`);
        return;
      }

      const progress = progressFlags.get(questionId);
      const duration = Date.now() - progress.startTime;
      
      // Clear timeout
      const timeoutId = timeouts.get(questionId);
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeouts.delete(questionId);
      }
      
      // Remove progress flag
      progressFlags.delete(questionId);
      
      console.log(`[EvaluationProgress] Completed: ${questionId} (${duration}ms, reason: ${reason})`);
    },

    /**
     * Force complete evaluation (for cleanup/timeout scenarios)
     * @param {string} questionId - Question ID
     * @param {string} reason - Reason for force completion
     */
    forceComplete: (questionId, reason = 'forced') => {
      manager.completeEvaluation(questionId, reason);
    },

    /**
     * Get all currently evaluating questions
     * @returns {Array} Array of question IDs currently evaluating
     */
    getCurrentlyEvaluating: () => {
      return Array.from(progressFlags.keys());
    },

    /**
     * Get evaluation status for a question
     * @param {string} questionId - Question ID
     * @returns {Object|null} Evaluation status or null if not in progress
     */
    getStatus: (questionId) => {
      const progress = progressFlags.get(questionId);
      if (!progress) return null;
      
      return {
        ...progress,
        duration: Date.now() - progress.startTime
      };
    },

    /**
     * Clear all evaluation flags (for cleanup)
     * @param {string} reason - Reason for clearing all
     */
    clearAll: (reason = 'cleanup') => {
      const questionIds = Array.from(progressFlags.keys());
      questionIds.forEach(questionId => {
        manager.completeEvaluation(questionId, reason);
      });
      console.log(`[EvaluationProgress] Cleared all evaluations (${questionIds.length}) - reason: ${reason}`);
    },

    /**
     * Get statistics about evaluations
     * @returns {Object} Statistics object
     */
    getStats: () => {
      const now = Date.now();
      const evaluations = Array.from(progressFlags.entries()).map(([questionId, progress]) => ({
        questionId,
        duration: now - progress.startTime,
        status: progress.status
      }));
      
      return {
        total: evaluations.length,
        evaluations,
        maxConcurrent: maxConcurrentEvaluations,
        timeoutMs
      };
    }
  };
  
  return manager;
};

/**
 * React Hook for managing evaluation progress with automatic cleanup
 * @param {Object} options - Configuration options
 * @returns {Object} Evaluation progress manager
 */
export const useEvaluationProgress = (options = {}) => {
  const manager = createEvaluationProgressManager(options);
  
  // Cleanup on component unmount
  React.useEffect(() => {
    return () => {
      manager.clearAll('component-unmount');
    };
  }, [manager]);

  return manager;
};

/**
 * Higher-order function to wrap async evaluation functions with progress tracking
 * @param {Function} evaluationFn - The evaluation function to wrap
 * @param {Object} progressManager - Progress manager instance
 * @returns {Function} Wrapped evaluation function
 */
export const withProgressTracking = (evaluationFn, progressManager) => {
  return async (questionId, ...args) => {
    // Start progress tracking
    if (!progressManager.startEvaluation(questionId)) {
      throw new Error(`Cannot start evaluation for ${questionId} - already in progress or limit reached`);
    }

    try {
      // Execute the evaluation
      const result = await evaluationFn(questionId, ...args);
      
      // Complete successfully
      progressManager.completeEvaluation(questionId, 'success');
      
      return result;
    } catch (error) {
      // Complete with error
      progressManager.completeEvaluation(questionId, 'error');
      throw error;
    }
  };
};

/**
 * Create a progress-aware evaluation queue
 * @param {Object} progressManager - Progress manager instance
 * @param {Function} evaluationFn - Function to evaluate questions
 * @returns {Object} Evaluation queue manager
 */
export const createEvaluationQueue = (progressManager, evaluationFn) => {
  const queue = [];
  let isProcessing = false;
  
  const processNext = async () => {
    if (isProcessing || queue.length === 0) return;
    
    isProcessing = true;
    
    while (queue.length > 0) {
      const { questionId, resolve, reject, args } = queue.shift();
      
      try {
        if (progressManager.startEvaluation(questionId)) {
          const result = await evaluationFn(questionId, ...args);
          progressManager.completeEvaluation(questionId, 'success');
          resolve(result);
        } else {
          // Skip if already in progress or limit reached
          resolve(null);
        }
      } catch (error) {
        progressManager.completeEvaluation(questionId, 'error');
        reject(error);
      }
    }
    
    isProcessing = false;
  };
  
  return {
    /**
     * Add evaluation to queue
     * @param {string} questionId - Question ID
     * @param {...any} args - Arguments for evaluation function
     * @returns {Promise} Promise that resolves when evaluation completes
     */
    enqueue: (questionId, ...args) => {
      return new Promise((resolve, reject) => {
        queue.push({ questionId, resolve, reject, args });
        processNext();
      });
    },
    
    /**
     * Get queue status
     * @returns {Object} Queue statistics
     */
    getQueueStatus: () => ({
      queueLength: queue.length,
      isProcessing,
      currentlyEvaluating: progressManager.getCurrentlyEvaluating()
    })
  };
};

export default {
  createEvaluationProgressManager,
  useEvaluationProgress,
  withProgressTracking,
  createEvaluationQueue
};