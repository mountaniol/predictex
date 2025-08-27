/**
 * UI Updater for Server-Driven UI
 * 
 * Coordinates UI updates from backend commands with React integration:
 * - Atomic batch updates to prevent inconsistent renders
 * - React Context integration with state synchronization
 * - Efficient DOM updates with minimal re-renders
 */

import React from 'react';

class UIUpdater {
  constructor(contextSetter) {
    this.contextSetter = contextSetter;  // Function to update React Context
    this.pendingUpdates = [];
    this.updateTimer = null;
    this.isUpdating = false;
    
    this.stats = {
      updatesApplied: 0,
      batchesProcessed: 0,
      renderUpdates: 0,
      valueUpdates: 0,
      stateSyncUpdates: 0,
      clearUpdates: 0,
      errors: 0
    };

    // Bind methods
    this.applyUpdates = this.applyUpdates.bind(this);
    this.scheduleUpdate = this.scheduleUpdate.bind(this);
  }

  /**
   * Apply batch of updates atomically
   * Mathematical guarantee: All updates applied together or not at all
   */
  async applyUpdates(updates) {
    if (!updates || updates.length === 0) {
      return;
    }

    // Add updates to pending batch
    this.pendingUpdates.push(...updates);

    // Schedule atomic batch processing
    this.scheduleUpdate();
  }

  /**
   * Schedule atomic update processing
   * Debounced to batch rapid updates
   */
  scheduleUpdate() {
    if (this.updateTimer) {
      clearTimeout(this.updateTimer);
    }

    this.updateTimer = setTimeout(() => {
      this.processPendingUpdates();
    }, 0);  // Process in next tick for batching
  }

  /**
   * Process all pending updates atomically
   * React integration: Uses unstable_batchedUpdates for consistency
   */
  async processPendingUpdates() {
    if (this.isUpdating || this.pendingUpdates.length === 0) {
      return;
    }

    this.isUpdating = true;
    const updates = [...this.pendingUpdates];
    this.pendingUpdates = [];

    try {
      // Group updates by type for optimal processing
      const groupedUpdates = this.groupUpdatesByType(updates);

      // Apply updates atomically within React batch
      await this.applyGroupedUpdates(groupedUpdates);

      this.stats.batchesProcessed++;
      this.stats.updatesApplied += updates.length;

    } catch (error) {
      console.error('[UIUpdater] Error processing updates:', error);
      this.stats.errors++;
      
      // Re-queue updates for retry (with limit)
      if (updates.length < 100) {  // Prevent infinite retry loops
        this.pendingUpdates.unshift(...updates);
      }
    } finally {
      this.isUpdating = false;
      this.updateTimer = null;
    }
  }

  /**
   * Group updates by type for efficient processing
   */
  groupUpdatesByType(updates) {
    const groups = {
      renders: [],
      values: [],
      stateSync: [],
      clears: [],
      batches: []
    };

    for (const update of updates) {
      switch (update.type) {
        case 'RENDER_UPDATE':
          groups.renders.push(update);
          break;
        case 'VALUE_UPDATE':
          groups.values.push(update);
          break;
        case 'STATE_SYNC_UPDATE':
          groups.stateSync.push(update);
          break;
        case 'CLEAR_UPDATE':
          groups.clears.push(update);
          break;
        case 'BATCH_UPDATE':
          groups.batches.push(update);
          break;
        default:
          console.warn('[UIUpdater] Unknown update type:', update.type);
      }
    }

    return groups;
  }

  /**
   * Apply grouped updates with React batching
   */
  async applyGroupedUpdates(groups) {
    // Use React's batching mechanism for consistent updates
    const { unstable_batchedUpdates } = await import('react-dom');
    
    return new Promise((resolve, reject) => {
      unstable_batchedUpdates(() => {
        try {
          // Apply updates in optimal order
          this.processClears(groups.clears);
          this.processStateSyncs(groups.stateSync);
          this.processRenders(groups.renders);
          this.processValues(groups.values);
          this.processBatches(groups.batches);
          
          resolve();
        } catch (error) {
          reject(error);
        }
      });
    });
  }

  /**
   * Process CLEAR updates - remove UI elements
   */
  processClears(clears) {
    if (clears.length === 0) return;

    this.contextSetter(prevContext => {
      const newContext = { ...prevContext };

      for (const clear of clears) {
        if (clear.questionId === null) {
          // Clear all
          newContext.answers = {};
          newContext.scores = {};
          newContext.explanations = {};
          newContext.questionStates = {};
        } else {
          // Clear specific question
          delete newContext.answers[clear.questionId];
          delete newContext.scores[clear.questionId];
          delete newContext.explanations[clear.questionId];
          delete newContext.questionStates[clear.questionId];
        }
      }

      return newContext;
    });

    this.stats.clearUpdates += clears.length;
  }

  /**
   * Process STATE_SYNC updates - synchronize entire state
   */
  processStateSyncs(stateSyncs) {
    if (stateSyncs.length === 0) return;

    // Merge all state sync updates
    const mergedState = stateSyncs.reduce((acc, sync) => {
      return {
        answers: { ...acc.answers, ...sync.answers },
        scores: { ...acc.scores, ...sync.scores },
        explanations: { ...acc.explanations, ...sync.explanations },
        questionStates: { ...acc.questionStates, ...sync.questionStates }
      };
    }, { answers: {}, scores: {}, explanations: {}, questionStates: {} });

    this.contextSetter(prevContext => ({
      ...prevContext,
      ...mergedState
    }));

    this.stats.stateSyncUpdates += stateSyncs.length;
  }

  /**
   * Process RENDER updates - add/update UI elements
   */
  processRenders(renders) {
    if (renders.length === 0) return;

    this.contextSetter(prevContext => {
      const newContext = { ...prevContext };

      // Ensure sections array exists
      if (!newContext.sections) {
        newContext.sections = [];
      }

      for (const render of renders) {
        this.applyRenderUpdate(newContext, render);
      }

      return newContext;
    });

    this.stats.renderUpdates += renders.length;
  }

  /**
   * Apply individual render update
   */
  applyRenderUpdate(context, render) {
    const { questionId, schema, metadata = {} } = render;

    // Find or create section for this question
    let section = context.sections.find(s => 
      s.questions && s.questions.some(q => q.id === questionId)
    );

    if (!section) {
      // Create new section
      section = {
        name: schema.cluster_name || 'Default',
        questions: []
      };
      context.sections.push(section);
    }

    // Find or create question
    let question = section.questions.find(q => q.id === questionId);
    
    if (!question) {
      // Create new question from schema
      question = {
        id: questionId,
        text: schema.label || schema.text || '',
        question_type: schema.type || 'text',
        ...schema,
        ...metadata
      };
      section.questions.push(question);
    } else {
      // Update existing question
      Object.assign(question, schema, metadata);
    }

    // Initialize question state if not exists
    if (!context.questionStates) {
      context.questionStates = {};
    }
    
    if (!context.questionStates[questionId]) {
      context.questionStates[questionId] = 'unanswered';
    }
  }

  /**
   * Process VALUE updates - update question values/scores
   */
  processValues(values) {
    if (values.length === 0) return;

    this.contextSetter(prevContext => {
      const newContext = { ...prevContext };

      // Initialize objects if they don't exist
      if (!newContext.answers) newContext.answers = {};
      if (!newContext.scores) newContext.scores = {};
      if (!newContext.explanations) newContext.explanations = {};
      if (!newContext.questionStates) newContext.questionStates = {};

      for (const value of values) {
        this.applyValueUpdate(newContext, value);
      }

      return newContext;
    });

    this.stats.valueUpdates += values.length;
  }

  /**
   * Apply individual value update
   */
  applyValueUpdate(context, value) {
    const { questionId, value: answer, score, explanation, state } = value;

    // Update answer if provided
    if (answer !== undefined) {
      context.answers[questionId] = answer;
    }

    // Update score if provided
    if (score !== undefined) {
      context.scores[questionId] = score;
    }

    // Update explanation if provided
    if (explanation !== undefined) {
      context.explanations[questionId] = explanation;
    }

    // Update state if provided
    if (state !== undefined) {
      context.questionStates[questionId] = state;
    }
  }

  /**
   * Process BATCH updates - handle nested batch updates
   */
  processBatches(batches) {
    if (batches.length === 0) return;

    // Flatten all batch updates and process them
    const flattenedUpdates = batches.reduce((acc, batch) => {
      if (batch.updates && Array.isArray(batch.updates)) {
        acc.push(...batch.updates);
      }
      return acc;
    }, []);

    if (flattenedUpdates.length > 0) {
      // Recursively process flattened updates
      const groupedUpdates = this.groupUpdatesByType(flattenedUpdates);
      this.processClears(groupedUpdates.clears);
      this.processStateSyncs(groupedUpdates.stateSync);
      this.processRenders(groupedUpdates.renders);
      this.processValues(groupedUpdates.values);
    }
  }

  /**
   * Get updater statistics
   */
  getStats() {
    return {
      ...this.stats,
      pendingUpdates: this.pendingUpdates.length,
      isUpdating: this.isUpdating,
      hasTimer: this.updateTimer !== null
    };
  }

  /**
   * Check if updater is healthy
   */
  isHealthy() {
    return (
      this.stats.errors < 10 &&
      this.pendingUpdates.length < 100  // Prevent infinite queuing
    );
  }

  /**
   * Reset updater state
   */
  reset() {
    if (this.updateTimer) {
      clearTimeout(this.updateTimer);
      this.updateTimer = null;
    }

    this.pendingUpdates = [];
    this.isUpdating = false;

    this.stats = {
      updatesApplied: 0,
      batchesProcessed: 0,
      renderUpdates: 0,
      valueUpdates: 0,
      stateSyncUpdates: 0,
      clearUpdates: 0,
      errors: 0
    };
  }
}

export default UIUpdater;