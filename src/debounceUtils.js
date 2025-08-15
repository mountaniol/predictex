/**
 * Debounce utility for delaying function execution
 * @file debounceUtils.js
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Creates a debounced version of a function that delays its execution
 * until after `delay` milliseconds have elapsed since the last time it was invoked.
 * 
 * @param {Function} func - The function to debounce
 * @param {number} delay - The delay in milliseconds
 * @returns {Function} The debounced function with cancel method
 */
export function debounce(func, delay) {
  let timeoutId = null;
  
  const debounced = function(...args) {
    // Clear any existing timeout
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    
    // Set a new timeout
    timeoutId = setTimeout(() => {
      func.apply(this, args);
      timeoutId = null;
    }, delay);
  };
  
  // Add cancel method to clear pending execution
  debounced.cancel = function() {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
  };
  
  // Add flush method to execute immediately
  debounced.flush = function(...args) {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    func.apply(this, args);
  };
  
  return debounced;
}

/**
 * React hook for debounced values
 * @param {any} value - The value to debounce
 * @param {number} delay - The delay in milliseconds
 * @returns {any} The debounced value
 */

export function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  
  return debouncedValue;
}

/**
 * React hook for debounced callback with automatic cleanup
 * @param {Function} callback - The callback to debounce
 * @param {number} delay - The delay in milliseconds
 * @param {Array} deps - Dependencies array
 * @returns {Object} Object with debounced function, cancel and flush methods
 */

export function useDebouncedCallback(callback, delay, deps = []) {
  const callbackRef = useRef(callback);
  const timeoutRef = useRef(null);
  
  // Update callback ref when it changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);
  
  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);
  
  const flush = useCallback((...args) => {
    cancel();
    callbackRef.current(...args);
  }, [cancel]);
  
  const debouncedCallback = useCallback((...args) => {
    cancel();
    
    timeoutRef.current = setTimeout(() => {
      callbackRef.current(...args);
      timeoutRef.current = null;
    }, delay);
  }, [delay, cancel]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);
  
  return {
    run: debouncedCallback,
    cancel,
    flush
  };
}