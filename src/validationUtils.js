/**
 * @file Shared validation utilities for QnA Evaluator
 * @summary Centralized validation logic to prevent code duplication and ensure
 * consistent behavior across all components.
 * @version 1.0.0
 * @author Predictex AI
 */

/**
 * Validates "Other" field logic for question answers
 * @param {Object} question - Question configuration object
 * @param {Array|string} selectedOptions - Selected option(s) for the question
 * @param {string} otherText - Text provided in the "Other" field
 * @returns {Object} Validation result with hasOther, hasText, isValid flags
 */
export const validateOtherField = (question, selectedOptions, otherText) => {
  if (!question.with_other || !question.other_text_id) {
    return { hasOther: false, hasText: false, isValid: true, isEmpty: false };
  }

  const isArray = Array.isArray(selectedOptions);
  const hasOther = isArray 
    ? selectedOptions.includes('other')
    : selectedOptions === 'other';
  
  const hasText = otherText && otherText.trim() !== '';
  
  // Check if ONLY "other" is selected without text
  const isOnlyOtherWithoutText = hasOther && !hasText && 
    (isArray ? selectedOptions.length === 1 : true);
  
  return {
    hasOther,
    hasText,
    isValid: !isOnlyOtherWithoutText, // Invalid if only "other" without text
    isEmpty: isOnlyOtherWithoutText,
    isOnlyOther: isArray ? selectedOptions.length === 1 && hasOther : hasOther
  };
};

/**
 * Comprehensive answer validation for a question
 * @param {Object} question - Question configuration object
 * @param {Object} answers - All current answers
 * @returns {Object} Validation result with detailed analysis
 */
export const validateQuestionAnswer = (question, answers) => {
  const answer = answers[question.id];
  const otherText = question.other_text_id ? answers[question.other_text_id] : null;
  const customText = question.custom_text_input ? answers[question.custom_text_input.id] : null;

  // Standard answer validation
  let hasStandardAnswer = false;
  if (answer !== undefined && answer !== null) {
    if (Array.isArray(answer)) {
      hasStandardAnswer = answer.length > 0;
    } else if (typeof answer === 'string') {
      hasStandardAnswer = answer.trim() !== '';
    } else {
      hasStandardAnswer = answer !== '';
    }
  }

  // "Other" field validation
  const otherValidation = validateOtherField(question, answer, otherText);
  
  // Custom text input validation
  const hasCustomAnswer = question.custom_text_input && 
    customText && customText.trim() !== '';

  // "Other" text answer validation (only counts if "other" is selected AND has text)
  const hasOtherTextAnswer = otherValidation.hasOther && otherValidation.hasText;

  // Final answer determination
  const hasValidAnswer = (hasStandardAnswer && otherValidation.isValid) || 
    hasCustomAnswer || hasOtherTextAnswer;

  return {
    hasValidAnswer,
    hasStandardAnswer,
    hasCustomAnswer,
    hasOtherTextAnswer,
    otherValidation,
    details: {
      answer,
      otherText,
      customText,
      questionType: question.question_type,
      hasOtherField: !!question.other_text_id,
      hasCustomInput: !!question.custom_text_input
    }
  };
};

/**
 * Validates answer for triggering AI evaluation
 * @param {Object} question - Question configuration object  
 * @param {Object} answers - All current answers
 * @returns {boolean} Whether this answer should trigger AI evaluation
 */
export const shouldTriggerAIEvaluation = (question, answers) => {
  // Questions with score="NO" never trigger AI
  if (question.score === "NO") {
    return false;
  }

  const validation = validateQuestionAnswer(question, answers);
  return validation.hasValidAnswer;
};

/**
 * Check if answer represents an empty/cleared state
 * @param {Object} question - Question configuration object
 * @param {Object} answers - All current answers
 * @returns {boolean} Whether the answer is effectively empty
 */
export const isAnswerEmpty = (question, answers) => {
  const validation = validateQuestionAnswer(question, answers);
  return !validation.hasValidAnswer;
};

/**
 * Get human-readable validation message
 * @param {Object} question - Question configuration object
 * @param {Object} answers - All current answers
 * @returns {string} Human-readable validation message
 */
export const getValidationMessage = (question, answers) => {
  const validation = validateQuestionAnswer(question, answers);
  
  if (validation.hasValidAnswer) {
    return "Valid answer provided";
  }
  
  if (validation.otherValidation.isEmpty) {
    return "Please provide text for 'Other' option or select a different option";
  }
  
  if (!validation.hasStandardAnswer && !validation.hasCustomAnswer) {
    return "Please provide an answer";
  }
  
  return "Invalid answer";
};

/**
 * Batch validate multiple questions
 * @param {Array} questions - Array of question objects
 * @param {Object} answers - All current answers
 * @returns {Object} Validation results keyed by question ID
 */
export const validateMultipleQuestions = (questions, answers) => {
  const results = {};
  
  questions.forEach(question => {
    if (question.question_type !== 'internal') {
      results[question.id] = validateQuestionAnswer(question, answers);
    }
  });
  
  return results;
};

/**
 * Check if questions have any validation errors
 * @param {Array} questions - Array of question objects
 * @param {Object} answers - All current answers
 * @returns {Array} Array of validation errors
 */
export const getValidationErrors = (questions, answers) => {
  const errors = [];
  
  questions.forEach(question => {
    if (question.question_type === 'internal') return;
    
    const validation = validateQuestionAnswer(question, answers);
    if (!validation.hasValidAnswer) {
      errors.push({
        questionId: question.id,
        questionText: question.text,
        message: getValidationMessage(question, answers),
        details: validation
      });
    }
  });
  
  return errors;
};

/**
 * Specialized validation for different question types
 */
export const questionTypeValidators = {
  'choice-single': (question, answer, otherText) => {
    if (!answer || answer === '') return false;
    if (answer === 'other') {
      return question.other_text_id ? (otherText && otherText.trim() !== '') : true;
    }
    return true;
  },
  
  'choice-multi': (question, answer, otherText) => {
    if (!Array.isArray(answer) || answer.length === 0) return false;
    if (answer.includes('other')) {
      return question.other_text_id ? (otherText && otherText.trim() !== '') : true;
    }
    return true;
  },
  
  'text': (question, answer) => {
    return answer && answer.trim() !== '';
  },
  
  'textarea': (question, answer) => {
    return answer && answer.trim() !== '';
  },
  
  'number': (question, answer) => {
    return answer !== undefined && answer !== null && answer !== '';
  },
  
  'yes-no': (question, answer) => {
    return answer && (answer === 'yes' || answer === 'no');
  }
};

/**
 * Validate answer based on question type
 * @param {Object} question - Question configuration object
 * @param {any} answer - Answer value
 * @param {string} otherText - Other field text if applicable
 * @returns {boolean} Whether answer is valid for this question type
 */
export const validateByQuestionType = (question, answer, otherText) => {
  const validator = questionTypeValidators[question.question_type];
  if (!validator) {
    console.warn(`[validationUtils] No validator for question type: ${question.question_type}`);
    return true; // Default to valid for unknown types
  }
  
  return validator(question, answer, otherText);
};

export default {
  validateOtherField,
  validateQuestionAnswer,
  shouldTriggerAIEvaluation,
  isAnswerEmpty,
  getValidationMessage,
  validateMultipleQuestions,
  getValidationErrors,
  validateByQuestionType,
  questionTypeValidators
};