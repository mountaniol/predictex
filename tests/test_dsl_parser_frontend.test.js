/**
 * Unit tests for the Follow-up DSL Parser (JavaScript Frontend)
 * 
 * This module tests the frontend DSL parser that processes follow-up rules
 * in TOML format and converts them to JSON format for backward compatibility.
 */

// Import the parser classes - adjust path as needed
import { FollowUpParser, FollowUpParserError } from '../src/utils/followUpParser.js';

describe('FollowUpParser', () => {
  let parser;

  beforeEach(() => {
    parser = new FollowUpParser();
  });

  describe('parseRule', () => {
    test('should parse a simple DSL rule', () => {
      const rule = "when:down_20plus -> ask:SG04_REASON:text:Main reason for decline:140";
      
      const expected = {
        when: { in: ['down_20plus'] },
        ask: {
          id: 'SG04_REASON',
          question_type: 'text',
          ui: 'text',
          placeholder: 'Main reason for decline',
          max_chars: 140
        }
      };
      
      const result = parser.parseRule(rule);
      expect(result).toEqual(expected);
    });

    test('should parse a DSL rule with textarea type', () => {
      const rule = "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120";
      
      const expected = {
        when: { in: ['yes'] },
        ask: {
          id: 'SG05_NOTE',
          question_type: 'text',
          ui: 'textarea',
          placeholder: 'Brief reason',
          max_chars: 120
        }
      };
      
      const result = parser.parseRule(rule);
      expect(result).toEqual(expected);
    });

    test('should parse a DSL rule without placeholder', () => {
      const rule = "when:cancelled -> ask:SG06_NOTES:textarea";
      
      const expected = {
        when: { in: ['cancelled'] },
        ask: {
          id: 'SG06_NOTES',
          question_type: 'text',
          ui: 'textarea'
        }
      };
      
      const result = parser.parseRule(rule);
      expect(result).toEqual(expected);
    });

    test('should parse a DSL rule with multiple conditions', () => {
      const rule = "when:high,critical -> ask:RISK_NOTE:text:Risk details:200";
      
      const expected = {
        when: { in: ['high', 'critical'] },
        ask: {
          id: 'RISK_NOTE',
          question_type: 'text',
          ui: 'text',
          placeholder: 'Risk details',
          max_chars: 200
        }
      };
      
      const result = parser.parseRule(rule);
      expect(result).toEqual(expected);
    });

    test('should parse DSL rules with choice question types', () => {
      const rule = "when:maybe -> ask:CHOICE_Q:choice-single";
      
      const expected = {
        when: { in: ['maybe'] },
        ask: {
          id: 'CHOICE_Q',
          question_type: 'choice-single',
          ui: 'radio'
        }
      };
      
      const result = parser.parseRule(rule);
      expect(result).toEqual(expected);
    });

    test('should throw error for invalid rule syntax', () => {
      expect(() => parser.parseRule("invalid rule")).toThrow(FollowUpParserError);
      expect(() => parser.parseRule("when:test")).toThrow(FollowUpParserError); // Missing arrow
      expect(() => parser.parseRule("-> ask:TEST:text")).toThrow(FollowUpParserError); // Missing when
    });

    test('should throw error for invalid question type', () => {
      expect(() => parser.parseRule("when:test -> ask:Q1:invalid_type")).toThrow(FollowUpParserError);
    });

    test('should throw error for invalid max_chars values', () => {
      expect(() => parser.parseRule("when:test -> ask:Q1:text:placeholder:abc")).toThrow(FollowUpParserError);
      expect(() => parser.parseRule("when:test -> ask:Q1:text:placeholder:-5")).toThrow(FollowUpParserError);
    });

    test('should throw error for empty rules', () => {
      expect(() => parser.parseRule("")).toThrow(FollowUpParserError);
      expect(() => parser.parseRule("   ")).toThrow(FollowUpParserError);
    });
  });

  describe('rulesToJson', () => {
    test('should convert a list of DSL rules to JSON format', () => {
      const rules = [
        "when:down_20plus -> ask:SG04_REASON:text:Main reason:140",
        "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120"
      ];
      
      const expected = [
        {
          when: { in: ['down_20plus'] },
          ask: {
            id: 'SG04_REASON',
            question_type: 'text',
            ui: 'text',
            placeholder: 'Main reason',
            max_chars: 140
          }
        },
        {
          when: { in: ['yes'] },
          ask: {
            id: 'SG05_NOTE',
            question_type: 'text',
            ui: 'textarea',
            placeholder: 'Brief reason',
            max_chars: 120
          }
        }
      ];
      
      const result = parser.rulesToJson(rules);
      expect(result).toEqual(expected);
    });

    test('should throw error for non-array input', () => {
      expect(() => parser.rulesToJson("not an array")).toThrow(FollowUpParserError);
    });
  });

  describe('jsonToRules', () => {
    test('should convert JSON follow-ups back to DSL format', () => {
      const followUps = [
        {
          when: { in: ['down_20plus'] },
          ask: {
            id: 'SG04_REASON',
            question_type: 'text',
            ui: 'text',
            placeholder: 'Main reason',
            max_chars: 140
          }
        }
      ];
      
      const result = parser.jsonToRules(followUps);
      expect(result).toHaveLength(1);
      expect(result[0]).toContain('when:down_20plus');
      expect(result[0]).toContain('ask:SG04_REASON:text');
      expect(result[0]).toContain('Main reason');
      expect(result[0]).toContain('140');
    });

    test('should throw error for non-array input', () => {
      expect(() => parser.jsonToRules("not an array")).toThrow(FollowUpParserError);
    });

    test('should throw error for invalid follow-up structure', () => {
      const invalidFollowUp = [{ invalid: 'structure' }];
      expect(() => parser.jsonToRules(invalidFollowUp)).toThrow(FollowUpParserError);
    });
  });

  describe('roundtrip conversion', () => {
    test('should maintain consistency in DSL -> JSON -> DSL conversion', () => {
      const originalRules = [
        "when:down_20plus -> ask:SG04_REASON:text:Main reason:140",
        "when:yes -> ask:SG05_NOTE:textarea:Brief reason:120"
      ];
      
      // Convert to JSON and back
      const jsonFormat = parser.rulesToJson(originalRules);
      const convertedRules = parser.jsonToRules(jsonFormat);
      
      // Should maintain the same number of rules
      expect(convertedRules).toHaveLength(originalRules.length);
      
      // Convert back to JSON to compare semantics
      const originalJson = parser.rulesToJson(originalRules);
      const convertedJson = parser.rulesToJson(convertedRules);
      expect(originalJson).toEqual(convertedJson);
    });
  });

  describe('validation methods', () => {
    test('should validate rule syntax correctly', () => {
      const validRule = "when:test -> ask:Q1:text:placeholder:100";
      const invalidRule = "invalid rule syntax";
      
      expect(parser.validateRuleSyntax(validRule)).toBe(true);
      expect(parser.validateRuleSyntax(invalidRule)).toBe(false);
    });

    test('should return supported question types', () => {
      const types = parser.getSupportedQuestionTypes();
      
      const expectedTypes = ['text', 'textarea', 'number', 'choice-single', 'choice-multi', 'yes-no'];
      expectedTypes.forEach(type => {
        expect(types).toContain(type);
      });
    });
  });

  describe('real-world examples from q4.toml', () => {
    test('should parse actual rules from q4.toml file', () => {
      // These are actual rules from the q4.toml file
      const realWorldRules = [
        "when:down_20plus -> ask:SG04_REASON:textarea:Main reason for decline:140",
        "when:yes -> ask:SG05_NOTE:textarea:Brief reason (seasonality/shock):120",
        "when:yes -> ask:SG12_REASON:textarea:Brief reason:120",
        "when:yes -> ask:SG25_REASON:textarea:Brief reason / fix:120"
      ];
      
      // Should parse all without errors
      realWorldRules.forEach(rule => {
        const result = parser.parseRule(rule);
        expect(result).toHaveProperty('when');
        expect(result).toHaveProperty('ask');
        expect(result.when).toHaveProperty('in');
        expect(result.ask).toHaveProperty('id');
        expect(result.ask).toHaveProperty('question_type');
      });
      
      // Test batch processing
      const jsonResults = parser.rulesToJson(realWorldRules);
      expect(jsonResults).toHaveLength(realWorldRules.length);
      
      // Test roundtrip
      const dslResults = parser.jsonToRules(jsonResults);
      expect(dslResults).toHaveLength(realWorldRules.length);
    });
  });

  describe('edge cases', () => {
    test('should handle whitespace in rules', () => {
      const rule = "  when:test  ->   ask:Q1:text:placeholder:100  ";
      
      const result = parser.parseRule(rule);
      expect(result.when.in).toEqual(['test']);
      expect(result.ask.id).toBe('Q1');
    });

    test('should handle special characters in placeholders', () => {
      const rule = "when:test -> ask:Q1:text:Brief reason (seasonality/shock):120";
      
      const result = parser.parseRule(rule);
      expect(result.ask.placeholder).toBe('Brief reason (seasonality/shock)');
    });

    test('should handle case insensitive when conditions', () => {
      const rule = "WHEN:TEST -> ASK:Q1:TEXT";
      
      // Should not throw error (case insensitive pattern matching)
      expect(() => parser.parseRule(rule)).not.toThrow();
    });
  });
});

describe('Utility functions', () => {
  test('parseFollowUpRules utility function', () => {
    const { parseFollowUpRules } = require('../src/utils/followUpParser.js');
    
    const rules = ["when:test -> ask:Q1:text:placeholder:100"];
    const result = parseFollowUpRules(rules);
    
    expect(result).toHaveLength(1);
    expect(result[0].when.in).toEqual(['test']);
  });

  test('convertFollowUpsToDsl utility function', () => {
    const { convertFollowUpsToDsl } = require('../src/utils/followUpParser.js');
    
    const followUps = [
      {
        when: { in: ['test'] },
        ask: { id: 'Q1', question_type: 'text', ui: 'text' }
      }
    ];
    
    const result = convertFollowUpsToDsl(followUps);
    expect(result).toHaveLength(1);
    expect(result[0]).toContain('when:test');
  });
});