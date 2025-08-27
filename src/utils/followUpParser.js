/**
 * Follow-up DSL Parser for JavaScript (Frontend)
 * 
 * This module provides parsing capabilities for the Domain Specific Language (DSL)
 * used to express follow-up question rules in a simplified, readable format.
 * 
 * This is the JavaScript/frontend counterpart to the Python backend parser.
 * Both parsers should produce identical results for the same input.
 */

/**
 * Custom error class for DSL parsing errors
 */
export class FollowUpParserError extends Error {
  constructor(message) {
    super(message);
    this.name = 'FollowUpParserError';
  }
}

/**
 * Follow-up DSL Parser class
 */
export class FollowUpParser {
  // Regex patterns for parsing DSL rules
  static DSL_PATTERN = /when:(?<condition>[^-]+)\s*->\s*ask:(?<questionSpec>.+)/i;
  static QUESTION_SPEC_PATTERN = /(?<id>[^:]+):(?<type>[^:]+)(?::(?<placeholder>[^:]+))?(?::(?<maxChars>[^:]+))?/;
  
  // Valid question types and their UI mappings
  static QUESTION_TYPE_MAPPING = {
    'text': 'text',
    'textarea': 'textarea',
    'number': 'number',
    'choice-single': 'radio',
    'choice-multi': 'multiselect',
    'yes-no': 'radio'
  };


  /**
   * Parse a single DSL rule string into follow-up object structure
   * 
   * @param {string} ruleString - DSL rule like "when:down_20plus -> ask:SG04_REASON:text:Main reason:140"
   * @returns {object} Dictionary with 'when' and 'ask' keys matching original JSON format
   * @throws {FollowUpParserError} If rule syntax is invalid
   */
  parseRule(ruleString) {
    if (!ruleString || typeof ruleString !== 'string' || !ruleString.trim()) {
      throw new FollowUpParserError("Rule string cannot be empty");
    }

    // Parse main DSL structure
    const match = ruleString.trim().match(FollowUpParser.DSL_PATTERN);
    if (!match) {
      throw new FollowUpParserError(`Invalid DSL rule syntax: ${ruleString}`);
    }

    const condition = match.groups.condition.trim();
    const questionSpec = match.groups.questionSpec.trim();

    // Parse condition (simple values or comma-separated list)
    const conditions = condition.split(',')
      .map(c => c.trim())
      .filter(c => c.length > 0);
    
    if (conditions.length === 0) {
      throw new FollowUpParserError(`No conditions found in rule: ${ruleString}`);
    }

    // Parse question specification
    const specMatch = questionSpec.match(FollowUpParser.QUESTION_SPEC_PATTERN);
    if (!specMatch) {
      throw new FollowUpParserError(`Invalid question specification: ${questionSpec}`);
    }

    const questionId = specMatch.groups.id.trim();
    const questionType = specMatch.groups.type.trim().toLowerCase();
    const placeholder = specMatch.groups.placeholder;
    const maxChars = specMatch.groups.maxChars;

    // Validate question type
    if (!(questionType in FollowUpParser.QUESTION_TYPE_MAPPING)) {
      const validTypes = Object.keys(FollowUpParser.QUESTION_TYPE_MAPPING).join(', ');
      throw new FollowUpParserError(
        `Invalid question type '${questionType}'. Valid types: ${validTypes}`
      );
    }

    // Build ask configuration
    const askConfig = {
      id: questionId,
      question_type: (['text', 'textarea'].includes(questionType)) ? 'text' : questionType,
      ui: FollowUpParser.QUESTION_TYPE_MAPPING[questionType]
    };

    // Add optional fields
    if (placeholder) {
      askConfig.placeholder = placeholder.trim();
    }

    if (maxChars) {
      const maxCharsStr = maxChars.trim();
      const maxCharsInt = parseInt(maxCharsStr, 10);
      
      if (isNaN(maxCharsInt)) {
        throw new FollowUpParserError(`Max chars must be integer: ${maxCharsStr}`);
      }
      
      if (maxCharsInt <= 0) {
        throw new FollowUpParserError(`Max chars must be positive integer: ${maxCharsStr}`);
      }
      
      askConfig.max_chars = maxCharsInt;
    }

    return {
      when: { in: conditions },
      ask: askConfig
    };
  }

  /**
   * Convert list of DSL rules to JSON follow-up format
   * 
   * @param {string[]} rules - List of DSL rule strings
   * @returns {object[]} List of follow-up objects in original JSON format
   * @throws {FollowUpParserError} If any rule is invalid
   */
  rulesToJson(rules) {
    if (!Array.isArray(rules)) {
      throw new FollowUpParserError("Rules must be an array");
    }

    const result = [];
    for (let i = 0; i < rules.length; i++) {
      try {
        const parsedRule = this.parseRule(rules[i]);
        result.push(parsedRule);
      } catch (error) {
        if (error instanceof FollowUpParserError) {
          throw new FollowUpParserError(`Error in rule ${i + 1}: ${error.message}`);
        }
        throw error;
      }
    }

    return result;
  }

  /**
   * Convert JSON follow-ups back to DSL format (for reverse conversion)
   * 
   * @param {object[]} followUps - List of follow-up objects in JSON format
   * @returns {string[]} List of DSL rule strings
   * @throws {FollowUpParserError} If JSON structure is invalid
   */
  jsonToRules(followUps) {
    if (!Array.isArray(followUps)) {
      throw new FollowUpParserError("Follow-ups must be an array");
    }

    const rules = [];
    for (let i = 0; i < followUps.length; i++) {
      try {
        const followUp = followUps[i];

        // Validate structure
        if (!followUp || typeof followUp !== 'object') {
          throw new FollowUpParserError(`Follow-up ${i + 1} must be an object`);
        }

        if (!followUp.when || !followUp.ask) {
          throw new FollowUpParserError(`Follow-up ${i + 1} missing 'when' or 'ask'`);
        }

        const whenClause = followUp.when;
        const askClause = followUp.ask;

        // Parse when clause
        if (!whenClause.in || !Array.isArray(whenClause.in) || whenClause.in.length === 0) {
          throw new FollowUpParserError(`Follow-up ${i + 1} 'when.in' must be non-empty array`);
        }

        const conditionStr = whenClause.in.join(',');

        // Parse ask clause
        const requiredFields = ['id', 'question_type'];
        for (const field of requiredFields) {
          if (!(field in askClause)) {
            throw new FollowUpParserError(`Follow-up ${i + 1} 'ask' missing '${field}'`);
          }
        }

        const questionId = askClause.id;
        const questionType = askClause.question_type;

        // Map question type based on UI hint
        const uiType = askClause.ui || '';
        let dslType;
        if (questionType === 'text' && uiType === 'textarea') {
          dslType = 'textarea';
        } else if (questionType === 'text') {
          dslType = 'text';
        } else {
          dslType = questionType;
        }

        // Build rule parts
        const ruleParts = [`when:${conditionStr}`, ' -> ', `ask:${questionId}:${dslType}`];

        // Add optional parts
        if (askClause.placeholder) {
          const placeholder = String(askClause.placeholder);
          ruleParts.push(`:${placeholder}`);

          if (askClause.max_chars) {
            const maxChars = askClause.max_chars;
            ruleParts.push(`:${maxChars}`);
          }
        }

        const ruleString = ruleParts.join('');
        rules.push(ruleString);

      } catch (error) {
        if (error instanceof FollowUpParserError) {
          throw error;
        }
        throw new FollowUpParserError(`Error converting follow-up ${i + 1}: ${error.message}`);
      }
    }

    return rules;
  }

  /**
   * Validate DSL rule syntax without full parsing
   * 
   * @param {string} ruleString - DSL rule to validate
   * @returns {boolean} True if syntax is valid, false otherwise
   */
  validateRuleSyntax(ruleString) {
    try {
      this.parseRule(ruleString);
      return true;
    } catch (error) {
      if (error instanceof FollowUpParserError) {
        return false;
      }
      throw error;
    }
  }

  /**
   * Get list of supported question types
   * 
   * @returns {string[]} List of valid question type strings
   */
  getSupportedQuestionTypes() {
    return Object.keys(FollowUpParser.QUESTION_TYPE_MAPPING);
  }
}

// Utility functions for module-level usage
/**
 * Utility function to parse follow-up rules
 * 
 * @param {string[]} rules - List of DSL rule strings
 * @returns {object[]} List of follow-up objects in JSON format
 */
export function parseFollowUpRules(rules) {
  const parser = new FollowUpParser();
  return parser.rulesToJson(rules);
}

/**
 * Utility function to convert JSON follow-ups to DSL
 * 
 * @param {object[]} followUps - List of follow-up objects in JSON format
 * @returns {string[]} List of DSL rule strings
 */
export function convertFollowUpsToDsl(followUps) {
  const parser = new FollowUpParser();
  return parser.jsonToRules(followUps);
}

// Default export
export default FollowUpParser;

// Example usage for testing (only in development)
if (typeof window !== 'undefined' && window.location && window.location.hostname === 'localhost') {
  // Test examples from q4.json (only in development)
  const testParser = () => {
    const parser = new FollowUpParser();
    
    // Test SG04 revenue decline follow-up
    const testRules = [
      "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140",
      "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120"
    ];
    
    console.log("Testing JavaScript DSL parsing:");
    testRules.forEach(rule => {
      try {
        const result = parser.parseRule(rule);
        console.log(`Rule: ${rule}`);
        console.log(`Parsed:`, result);
      } catch (error) {
        console.error(`Error parsing '${rule}':`, error.message);
      }
    });
    
    // Test roundtrip conversion
    console.log("Testing roundtrip conversion:");
    try {
      const jsonResult = parser.rulesToJson(testRules);
      const dslResult = parser.jsonToRules(jsonResult);
      console.log(`Original DSL:`, testRules);
      console.log(`Converted back:`, dslResult);
      console.log(`Roundtrip success:`, JSON.stringify(testRules) === JSON.stringify(dslResult));
    } catch (error) {
      console.error("Roundtrip test failed:", error.message);
    }
  };

  // Auto-run test in development
  if (typeof window !== 'undefined' && window.followUpParserTest !== true) {
    window.followUpParserTest = true;
    setTimeout(testParser, 100);
  }
}