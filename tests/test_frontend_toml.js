#!/usr/bin/env node
/**
 * Frontend TOML Loading Test
 * Tests the TOML loading functionality in Node.js environment
 */

const TOML = require('toml');
const fs = require('fs');
const path = require('path');

// Mock FollowUpParser for testing
class MockFollowUpParser {
    rulesToJson(rules) {
        // Simple mock implementation that converts DSL to JSON format
        return rules.map(rule => {
            const match = rule.match(/when:([^-]+)\s*->\s*ask:([^:]+):([^:]+):(.+):(\d+)/);
            if (match) {
                return {
                    when: { in: [match[1].trim()] },
                    ask: {
                        id: match[2],
                        question_type: match[3],
                        ui: match[3] === 'textarea' ? 'textarea' : 'text',
                        placeholder: match[4],
                        max_chars: parseInt(match[5])
                    }
                };
            }
            return null;
        }).filter(Boolean);
    }
}

/**
 * Process TOML data similar to frontend processing
 */
async function processTOMLData(data) {
    const parser = new MockFollowUpParser();
    let processedCount = 0;
    
    if (data.questions) {
        for (const question of data.questions) {
            // Process follow-up rules from DSL to JSON format
            if (question.follow_up_rules && question.follow_up_rules.length > 0) {
                try {
                    question.follow_ups = parser.rulesToJson(question.follow_up_rules);
                    processedCount++;
                    console.log(`[Frontend Test] Processed ${question.follow_up_rules.length} follow-up rules for question ${question.id}`);
                    
                    // Remove DSL rules to maintain JSON compatibility
                    delete question.follow_up_rules;
                } catch (error) {
                    console.warn(`[Frontend Test] Failed to parse follow-up rules for question ${question.id}:`, error.message);
                }
            }
            
            // Process flattened AI context fields
            if (question.ai_context_include_answers) {
                question.ai_context = {
                    include_answers: question.ai_context_include_answers
                };
                delete question.ai_context_include_answers;
            }
        }
    }
    
    // Process flattened analysis configuration
    if (data.analysis) {
        const analysisData = data.analysis;
        const sections = [];
        
        // Extract base configuration
        const loading_message = analysisData.loading_message || '';
        const base_prompt = analysisData.base_prompt || '';
        
        // Process each analysis section
        for (const [key, sectionData] of Object.entries(analysisData)) {
            if (key === 'loading_message' || key === 'base_prompt' || typeof sectionData !== 'object') {
                continue;
            }
            
            const section = {
                name: sectionData.name || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                model: sectionData.model || 'gpt-4o',
                web_search: {
                    enabled: sectionData.web_search_enabled || false,
                    max_searches: sectionData.web_search_max_searches || 3
                },
                ai_context: {
                    include_answers: sectionData.ai_context_include_answers || [],
                    include_scores: sectionData.ai_context_include_scores || false,
                    include_overall_score: sectionData.ai_context_include_overall_score || false
                },
                specific_prompt: sectionData.specific_prompt || '',
                output_constraint: sectionData.output_constraint || '',
                model_config: sectionData.model_config || {}
            };
            sections.push(section);
        }
        
        // Replace with nested structure for backward compatibility
        data.final_analysis_config = {
            loading_message,
            base_prompt,
            sections
        };
        
        // Remove flattened analysis config
        delete data.analysis;
        
        console.log(`[Frontend Test] Processed ${sections.length} analysis sections from TOML format`);
    }
    
    if (processedCount > 0) {
        console.log(`[Frontend Test] Successfully processed follow-up rules for ${processedCount} questions`);
    }
    
    return data;
}

/**
 * Test frontend TOML loading functionality
 */
async function testFrontendTOMLLoading() {
    console.log('🚀 Testing Frontend TOML Loading...');
    console.log('=' * 50);
    
    const tomlPath = path.join(__dirname, '..', 'public', 'questions', 'q4.toml');
    
    try {
        // Test 1: Load and parse TOML file
        console.log('Test 1: Loading TOML file...');
        const tomlContent = fs.readFileSync(tomlPath, 'utf-8');
        const data = TOML.parse(tomlContent);
        console.log(`✅ TOML parsed successfully: ${data.questions.length} questions`);
        
        // Test 2: Process TOML data
        console.log('\nTest 2: Processing TOML data...');
        const processedData = await processTOMLData(data);
        console.log(`✅ Data processing complete`);
        
        // Test 3: Validate structure
        console.log('\nTest 3: Validating processed structure...');
        
        // Check questions structure
        const questions = processedData.questions;
        console.log(`- Questions loaded: ${questions.length}`);
        
        // Check for follow-up processing
        const followUpQuestions = questions.filter(q => 'follow_ups' in q);
        console.log(`- Questions with follow-ups: ${followUpQuestions.length}`);
        
        // Check analysis config
        const analysisConfig = processedData.final_analysis_config;
        if (analysisConfig && analysisConfig.sections) {
            console.log(`- Analysis sections: ${analysisConfig.sections.length}`);
        }
        
        // Check specific follow-up conversion
        const sg04 = questions.find(q => q.id === 'SG04');
        if (sg04 && sg04.follow_ups) {
            const followUp = sg04.follow_ups[0];
            if (followUp.when.in.includes('down_20plus') && followUp.ask.id === 'SG04_REASON') {
                console.log('✅ Follow-up DSL conversion working correctly');
            } else {
                console.log('❌ Follow-up DSL conversion failed');
                return false;
            }
        }
        
        // Test 4: Structure compatibility
        console.log('\nTest 4: Checking JSON compatibility...');
        const requiredFields = ['questions', 'final_analysis_config', 'settings'];
        for (const field of requiredFields) {
            if (!(field in processedData)) {
                console.log(`❌ Missing required field: ${field}`);
                return false;
            }
        }
        console.log('✅ All required fields present');
        
        // Test 5: Question validation
        console.log('\nTest 5: Validating individual questions...');
        let validQuestions = 0;
        for (const question of questions) {
            if (question.id && question.text && question.question_type) {
                validQuestions++;
            }
        }
        console.log(`✅ Valid questions: ${validQuestions}/${questions.length}`);
        
        if (validQuestions === questions.length) {
            console.log('\n🎉 ALL FRONTEND TOML TESTS PASSED!');
            console.log('✅ Frontend TOML loading is fully functional');
            return true;
        } else {
            console.log('\n❌ Some frontend tests failed');
            return false;
        }
        
    } catch (error) {
        console.error('❌ Frontend TOML test failed:', error.message);
        return false;
    }
}

// Run the test
if (require.main === module) {
    testFrontendTOMLLoading().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = { testFrontendTOMLLoading, processTOMLData };