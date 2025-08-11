/**
 * @file calculationUtils.js
 * @brief Utility functions for applying calculation rules to scores.
 */

/**
 * Applies a series of calculation rules to a base set of scores.
 *
 * @param {object} baseScores - The initial scores object (e.g., {ID1: 50, ID2: 75}).
 * @param {Array<string>} calculations - An array of strings, where each string is a calculation rule (e.g., "OVERALL = (ID1 + ID2) / 2").
 * @returns {object} A new scores object with the calculated values included.
 */
export const applyCalculations = (baseScores, calculations) => {
  const newScores = { ...baseScores };
  if (!calculations) return newScores;

  const idRegex = /\b([A-Z]+[0-9]+[A-Z]?)\b/g;

  calculations.forEach(line => {
    if (!line || typeof line !== 'string') return;

    const parts = line.split('=');
    if (parts.length !== 2) return;

    const target = parts[0].trim();
    let expr = parts[1].trim();

    // Find all dependency IDs in the expression
    const dependencies = (expr.match(idRegex) || []);
    
    // Check if all dependencies are present in the newScores object
    const allDependenciesMet = dependencies.every(id => newScores[id] !== undefined);

    if (allDependenciesMet) {
      // Replace IDs with their values
      expr = expr.replace(idRegex, (match, id) => `(newScores['${id}'])`);
      try {
        // eslint-disable-next-line no-new-func
        const value = new Function('newScores', `return ${expr}`)(newScores);
        if (Number.isFinite(value)) {
          newScores[target] = value;
        }
      } catch (e) {
        console.error(`[applyCalculations] Error evaluating expression "${line}":`, e);
      }
    }
  });

  return newScores;
};
