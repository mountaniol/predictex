/**
 * @file Memory management utilities for QnA Evaluator
 * @summary Centralized memory management to prevent ref accumulation and memory leaks
 * @version 1.0.0
 * @author Predictex AI
 */

/**
 * Creates a managed ref that automatically cleans up old entries
 * @param {Object} options - Configuration options
 * @returns {Object} Managed ref with cleanup capabilities
 */
export const createManagedRef = (options = {}) => {
  const {
    maxEntries = 1000, // Maximum entries before triggering cleanup
    cleanupThreshold = 0.8, // Clean when 80% of maxEntries reached
    ttlMs = 24 * 60 * 60 * 1000, // Time to live: 24 hours
    onCleanup = (removedCount) => console.log(`[MemoryManager] Cleaned up ${removedCount} old entries`)
  } = options;

  const data = new Map();
  const timestamps = new Map();

  const manager = {
    /**
     * Set value with automatic timestamp tracking
     * @param {string} key - Key to set
     * @param {any} value - Value to set
     */
    set: (key, value) => {
      data.set(key, value);
      timestamps.set(key, Date.now());
      
      // Trigger cleanup if needed
      if (data.size >= maxEntries * cleanupThreshold) {
        manager.cleanup();
      }
    },

    /**
     * Get value from the managed ref
     * @param {string} key - Key to get
     * @returns {any} Stored value or undefined
     */
    get: (key) => {
      return data.get(key);
    },

    /**
     * Check if key exists
     * @param {string} key - Key to check
     * @returns {boolean} Whether key exists
     */
    has: (key) => {
      return data.has(key);
    },

    /**
     * Delete specific key
     * @param {string} key - Key to delete
     */
    delete: (key) => {
      data.delete(key);
      timestamps.delete(key);
    },

    /**
     * Clean up old entries based on TTL and usage
     * @param {boolean} force - Force cleanup regardless of threshold
     * @returns {number} Number of entries removed
     */
    cleanup: (force = false) => {
      const now = Date.now();
      const initialSize = data.size;
      let removedCount = 0;

      // Remove expired entries (TTL-based cleanup)
      for (const [key, timestamp] of timestamps.entries()) {
        if (now - timestamp > ttlMs) {
          data.delete(key);
          timestamps.delete(key);
          removedCount++;
        }
      }

      // If still over threshold, remove oldest entries
      if (force || data.size >= maxEntries * cleanupThreshold) {
        const entries = Array.from(timestamps.entries())
          .sort((a, b) => a[1] - b[1]); // Sort by timestamp (oldest first)
        
        const targetSize = Math.floor(maxEntries * 0.6); // Clean down to 60% of max
        const toRemove = Math.max(0, data.size - targetSize);
        
        for (let i = 0; i < toRemove && i < entries.length; i++) {
          const [key] = entries[i];
          data.delete(key);
          timestamps.delete(key);
          removedCount++;
        }
      }

      if (removedCount > 0) {
        onCleanup(removedCount);
      }

      return removedCount;
    },

    /**
     * Clear all entries
     */
    clear: () => {
      const count = data.size;
      data.clear();
      timestamps.clear();
      if (count > 0) {
        onCleanup(count);
      }
    },

    /**
     * Get current statistics
     * @returns {Object} Statistics about memory usage
     */
    getStats: () => {
      const now = Date.now();
      const ages = Array.from(timestamps.values()).map(ts => now - ts);
      
      return {
        totalEntries: data.size,
        maxEntries,
        utilizationPercent: (data.size / maxEntries) * 100,
        oldestEntryAge: ages.length > 0 ? Math.max(...ages) : 0,
        averageAge: ages.length > 0 ? ages.reduce((sum, age) => sum + age, 0) / ages.length : 0,
        entriesNearExpiry: ages.filter(age => age > ttlMs * 0.8).length
      };
    },

    /**
     * Validate against known question IDs to remove orphaned entries
     * @param {Array} validQuestionIds - Array of currently valid question IDs
     * @returns {number} Number of orphaned entries removed
     */
    validateAgainstQuestions: (validQuestionIds) => {
      const validIds = new Set(validQuestionIds);
      let removedCount = 0;

      for (const key of data.keys()) {
        if (!validIds.has(key)) {
          data.delete(key);
          timestamps.delete(key);
          removedCount++;
        }
      }

      if (removedCount > 0) {
        console.log(`[MemoryManager] Removed ${removedCount} orphaned entries`);
      }

      return removedCount;
    },

    /**
     * Create a lightweight version that only tracks existence (for boolean flags)
     * @returns {Object} Set-like interface for boolean flags
     */
    createFlagManager: () => {
      const flags = new Set();
      const flagTimestamps = new Map();

      return {
        add: (key) => {
          flags.add(key);
          flagTimestamps.set(key, Date.now());
        },
        
        has: (key) => flags.has(key),
        
        delete: (key) => {
          flags.delete(key);
          flagTimestamps.delete(key);
        },
        
        clear: () => {
          flags.clear();
          flagTimestamps.clear();
        },
        
        cleanup: () => {
          const now = Date.now();
          let removed = 0;
          
          for (const [key, timestamp] of flagTimestamps.entries()) {
            if (now - timestamp > ttlMs) {
              flags.delete(key);
              flagTimestamps.delete(key);
              removed++;
            }
          }
          
          return removed;
        },
        
        size: () => flags.size
      };
    }
  };

  return manager;
};

/**
 * Create a simple ref wrapper for compatibility with existing useRef patterns
 * @param {any} initialValue - Initial value for the ref
 * @param {Object} options - Management options
 * @returns {Object} Ref-like object with current property and memory management
 */
export const createManagedRefWrapper = (initialValue, options = {}) => {
  const manager = createManagedRef(options);
  
  return {
    current: initialValue,
    manager,
    
    // Helper methods for common ref patterns
    set: (key, value) => manager.set(key, value),
    get: (key) => manager.get(key),
    has: (key) => manager.has(key),
    delete: (key) => manager.delete(key),
    cleanup: () => manager.cleanup(),
    clear: () => manager.clear(),
    getStats: () => manager.getStats()
  };
};

/**
 * Create a batch cleanup manager for multiple refs
 * @param {Array} managedRefs - Array of managed refs to coordinate
 * @returns {Object} Batch cleanup manager
 */
export const createBatchCleanupManager = (managedRefs = []) => {
  let scheduledCleanup = null;

  return {
    /**
     * Add ref to batch cleanup
     * @param {Object} managedRef - Managed ref to add
     */
    addRef: (managedRef) => {
      managedRefs.push(managedRef);
    },

    /**
     * Schedule cleanup for all refs
     * @param {number} delay - Delay in milliseconds
     */
    scheduleCleanup: (delay = 1000) => {
      if (scheduledCleanup) {
        clearTimeout(scheduledCleanup);
      }

      scheduledCleanup = setTimeout(() => {
        const totalRemoved = managedRefs.reduce((total, ref) => {
          return total + ref.cleanup();
        }, 0);

        if (totalRemoved > 0) {
          console.log(`[BatchCleanup] Removed ${totalRemoved} total entries across ${managedRefs.length} refs`);
        }

        scheduledCleanup = null;
      }, delay);
    },

    /**
     * Force immediate cleanup of all refs
     */
    forceCleanupAll: () => {
      if (scheduledCleanup) {
        clearTimeout(scheduledCleanup);
        scheduledCleanup = null;
      }

      managedRefs.forEach(ref => ref.cleanup(true));
    },

    /**
     * Get combined statistics from all refs
     */
    getAggregateStats: () => {
      const stats = managedRefs.map(ref => ref.getStats());
      
      return {
        totalRefs: managedRefs.length,
        totalEntries: stats.reduce((sum, s) => sum + s.totalEntries, 0),
        totalUtilization: stats.reduce((sum, s) => sum + s.utilizationPercent, 0) / stats.length,
        oldestEntry: Math.max(...stats.map(s => s.oldestEntryAge)),
        refsNeedingCleanup: stats.filter(s => s.utilizationPercent > 70).length
      };
    }
  };
};

export default {
  createManagedRef,
  createManagedRefWrapper,
  createBatchCleanupManager
};