import { createDependencyReport } from './src/dependencyValidator.js';

// Test circular dependency: A -> B -> C -> A
const circularTest = {
  questions: [
    {
      id: "A",
      text: "Question A",
      question_type: "text",
      ai_context: { include_answers: ["C"] }
    },
    {
      id: "B", 
      text: "Question B",
      question_type: "text",
      ai_context: { include_answers: ["A"] }
    },
    {
      id: "C",
      text: "Question C",
      question_type: "text", 
      ai_context: { include_answers: ["B"] }
    }
  ]
};

console.log("=== CIRCULAR DEPENDENCY TEST ===");
const circularReport = createDependencyReport(circularTest.questions);
console.log(`Valid: ${circularReport.validation.isValid}`);
console.log(`Errors: ${circularReport.validation.errors.length}`);
console.log(`Circular deps: ${circularReport.validation.stats.circularDependencies.length}`);
circularReport.validation.errors.forEach(error => console.log(`  ${error}`));

// Test valid DAG
const validTest = {
  questions: [
    {
      id: "ROOT",
      text: "Root Question",
      question_type: "text",
      ai_context: { include_answers: [] }
    },
    {
      id: "CHILD1",
      text: "Child Question 1", 
      question_type: "text",
      ai_context: { include_answers: ["ROOT"] }
    },
    {
      id: "CHILD2",
      text: "Child Question 2",
      question_type: "text",
      ai_context: { include_answers: ["ROOT"] }
    },
    {
      id: "GRANDCHILD",
      text: "Grandchild Question",
      question_type: "text",
      ai_context: { include_answers: ["CHILD1", "CHILD2"] }
    }
  ]
};

console.log("\n=== VALID DAG TEST ===");
const validReport = createDependencyReport(validTest.questions);
console.log(`Valid: ${validReport.validation.isValid}`);
console.log(`Errors: ${validReport.validation.errors.length}`);
console.log(`Topo sort valid: ${validReport.topologicalSort.isValid}`);
console.log(`Sorted order: ${validReport.topologicalSort.sortedOrder.join(' -> ')}`);

// Test missing reference
const missingRefTest = {
  questions: [
    {
      id: "EXISTING",
      text: "Existing Question",
      question_type: "text", 
      ai_context: { include_answers: ["MISSING"] }
    }
  ]
};

console.log("\n=== MISSING REFERENCE TEST ===");
const missingReport = createDependencyReport(missingRefTest.questions);
console.log(`Valid: ${missingReport.validation.isValid}`);
console.log(`Errors: ${missingReport.validation.errors.length}`);
console.log(`Missing refs: ${missingReport.validation.stats.missingReferences.length}`);
missingReport.validation.errors.forEach(error => console.log(`  ${error}`));

console.log("\n=== RECOMMENDATIONS ===");
[circularReport, validReport, missingReport].forEach((report, i) => {
  console.log(`Test ${i+1}:`);
  report.recommendations.forEach(rec => console.log(`  ${rec}`));
});