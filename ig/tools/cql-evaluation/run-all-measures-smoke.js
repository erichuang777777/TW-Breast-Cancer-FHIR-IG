const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const cql = require('cql-execution');
const cqlfhir = require('cql-exec-fhir');

const [mainPath, helpersPath, casesPath, valueSetsPath, measureDirectory] = process.argv.slice(2);
if (!measureDirectory) {
  throw new Error(
    'usage: node run-all-measures-smoke.js <main-elm> <fhirhelpers-elm> <cases> <value-sets> <measure-directory>'
  );
}

const readJson = filePath => JSON.parse(fs.readFileSync(filePath, 'utf8'));
const mainElm = readJson(mainPath);
const helpersElm = readJson(helpersPath);
const testCases = readJson(casesPath);
const valueSets = readJson(valueSetsPath);

// Register the released FHIRHelpers ELM under the namespace requested by the
// translated main ELM. See run-bc-qi-01.js for the package-loader rationale.
const helpersInclude = mainElm.library.includes?.def?.find(
  include => include.localIdentifier === 'FHIRHelpers'
);
const helpersIdentifier = helpersElm.library?.identifier;
assert.ok(helpersInclude?.path, 'main ELM has no FHIRHelpers include path');
assert.equal(helpersIdentifier?.id, 'FHIRHelpers');
assert.equal(helpersIdentifier?.version, helpersInclude.version);
const helperSuffix = `/${helpersIdentifier.id}`;
if (helpersInclude.path.endsWith(helperSuffix)) {
  helpersIdentifier.system = helpersInclude.path.slice(0, -helperSuffix.length);
}

function criteriaExpressions(measure) {
  const expressions = [];
  for (const group of measure.group || []) {
    for (const population of group.population || []) {
      assert.equal(
        population.criteria?.language,
        'text/cql-identifier',
        `${measure.id}: population criteria is not a CQL identifier`
      );
      expressions.push(population.criteria.expression);
    }
    for (const stratifier of group.stratifier || []) {
      assert.equal(
        stratifier.criteria?.language,
        'text/cql-identifier',
        `${measure.id}: stratifier criteria is not a CQL identifier`
      );
      expressions.push(stratifier.criteria.expression);
    }
  }
  assert.ok(expressions.length, `${measure.id}: no executable criteria`);
  return [...new Set(expressions)];
}

const measureFiles = fs.readdirSync(measureDirectory)
  .filter(fileName => /^Measure-bc-(qi|qr)-\d+\.json$/.test(fileName))
  .sort();
const measures = measureFiles.map(fileName => readJson(path.join(measureDirectory, fileName)));
assert.equal(measures.length, 20, `expected 20 case-management Measures, found ${measures.length}`);
assert.equal(new Set(measures.map(measure => measure.id)).size, 20, 'Measure ids are not unique');

const coverage = Object.fromEntries(
  measures.map(measure => [measure.id, criteriaExpressions(measure)])
);
const expressions = [...new Set(Object.values(coverage).flat())].sort();

const repository = new cql.Repository({ main: mainElm, FHIRHelpers: helpersElm });
const library = new cql.Library(mainElm, repository);
const codeService = new cql.CodeService(valueSets);
const executor = new cql.Executor(library, codeService, {
  'Measurement Period': new cql.Interval(
    new cql.DateTime(2026, 1, 1, 0, 0, 0, 0, 8),
    new cql.DateTime(2026, 12, 31, 23, 59, 59, 999, 8),
    true,
    true
  )
});

function patientId(testCase) {
  const patients = testCase.bundle.entry
    .map(entry => entry.resource)
    .filter(resource => resource.resourceType === 'Patient');
  assert.equal(patients.length, 1, `${testCase.id}: expected exactly one Patient`);
  return patients[0].id;
}

async function evaluate(expression) {
  const source = cqlfhir.PatientSource.FHIRv401();
  source.loadBundles(testCases.map(testCase => testCase.bundle));
  return (await executor.exec_expression(expression, source)).patientResults;
}

async function main() {
  const actualByExpression = {};
  for (const expression of expressions) {
    actualByExpression[expression] = await evaluate(expression);
  }

  for (const testCase of testCases) {
    const id = patientId(testCase);
    for (const expression of expressions) {
      const result = actualByExpression[expression][id];
      assert.ok(result, `${testCase.id}: no result for ${expression}`);
      assert.ok(
        Object.prototype.hasOwnProperty.call(result, expression),
        `${testCase.id}: result omitted ${expression}`
      );
    }
    for (const [expression, expected] of Object.entries(testCase.expected || {})) {
      assert.deepEqual(
        actualByExpression[expression][id][expression],
        expected,
        `${testCase.id}: ${expression}`
      );
    }
  }

  process.stdout.write(`${JSON.stringify({
    measures: measures.length,
    expressions: expressions.length,
    cases: testCases.length,
    coverage
  })}\n`);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
