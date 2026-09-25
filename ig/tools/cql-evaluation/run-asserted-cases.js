const assert = require('node:assert/strict');
const fs = require('node:fs');

const cql = require('cql-execution');
const cqlfhir = require('cql-exec-fhir');

const [mainPath, helpersPath, casesPath, valueSetsPath] = process.argv.slice(2);
if (!valueSetsPath) {
  throw new Error(
    'usage: node run-asserted-cases.js <main-elm> <fhirhelpers-elm> <cases> <value-sets>'
  );
}

const readJson = filePath => JSON.parse(fs.readFileSync(filePath, 'utf8'));
const mainElm = readJson(mainPath);
const helpersElm = readJson(helpersPath);
const testCases = readJson(casesPath);
const valueSets = readJson(valueSetsPath);

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

const repository = new cql.Repository({ main: mainElm, FHIRHelpers: helpersElm });
const library = new cql.Library(mainElm, repository);
const codeService = new cql.CodeService(valueSets);

function parametersFor(testCase) {
  return {
    'Measurement Period': new cql.Interval(
      new cql.DateTime(2026, 1, 1, 0, 0, 0, 0, 8),
      new cql.DateTime(2026, 12, 31, 23, 59, 59, 999, 8),
      true,
      true
    ),
    ...(testCase.parameters || {})
  };
}

function patientId(testCase) {
  const patients = testCase.bundle.entry
    .map(entry => entry.resource)
    .filter(resource => resource.resourceType === 'Patient');
  assert.equal(patients.length, 1, `${testCase.id}: expected exactly one Patient`);
  return patients[0].id;
}

async function main() {
  const coveredExpressions = new Set();
  for (const testCase of testCases) {
    assert.ok(testCase.id, 'case has no id');
    assert.ok(testCase.expected && Object.keys(testCase.expected).length, `${testCase.id}: no assertions`);
    const executor = new cql.Executor(library, codeService, parametersFor(testCase));
    const id = patientId(testCase);

    for (const [expression, expected] of Object.entries(testCase.expected)) {
      // PatientSource is an iterator and is exhausted by each execution.
      // Recreate it for every expression so later assertions cannot silently
      // disappear after the first patient has been consumed.
      const source = cqlfhir.PatientSource.FHIRv401();
      source.loadBundles([testCase.bundle]);
      const execution = await executor.exec_expression(expression, source);
      const result = execution.patientResults[id];
      assert.ok(result, `${testCase.id}: no result for ${expression}`);
      assert.ok(
        Object.prototype.hasOwnProperty.call(result, expression),
        `${testCase.id}: result omitted ${expression}`
      );
      assert.deepEqual(result[expression], expected, `${testCase.id}: ${expression}`);
      coveredExpressions.add(expression);
    }
  }

  process.stdout.write(`${JSON.stringify({
    cases: testCases.length,
    assertedExpressions: [...coveredExpressions].sort()
  })}\n`);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
