const assert = require('node:assert/strict');
const fs = require('node:fs');

const cql = require('cql-execution');
const cqlfhir = require('cql-exec-fhir');

const [mainPath, helpersPath, casesPath, valueSetsPath, expectedReportPath] = process.argv.slice(2);
if (!expectedReportPath) {
  throw new Error(
    'usage: node run-bc-qi-01.js <main-elm> <fhirhelpers-elm> <cases> <value-sets> <expected-report>'
  );
}

const readJson = path => JSON.parse(fs.readFileSync(path, 'utf8'));
const mainElm = readJson(mainPath);
const helpersElm = readJson(helpersPath);
const testCases = readJson(casesPath);
const valueSets = readJson(valueSetsPath);
const expectedReport = readJson(expectedReportPath);

// cql-to-elm resolves the built-in FHIR model helper to an include path such
// as http://hl7.org/fhir/FHIRHelpers, while the released CQL package correctly
// identifies the same helper as http://hl7.org/fhir/uv/cql/FHIRHelpers.  The
// JavaScript repository resolves strictly by ELM identifier URI, so register
// the package ELM under the exact path requested by the translated main ELM.
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
const parameters = {
  'Measurement Period': new cql.Interval(
    new cql.DateTime(2026, 1, 1, 0, 0, 0, 0, 8),
    new cql.DateTime(2026, 12, 31, 23, 59, 59, 999, 8),
    true,
    true
  )
};
const executor = new cql.Executor(library, codeService, parameters);
const expressions = [
  'Initial Population',
  'Denominator 1',
  'Denominator 1 Exclusion',
  'Numerator 1'
];

async function evaluate(expression) {
  const source = cqlfhir.PatientSource.FHIRv401();
  source.loadBundles(testCases.map(testCase => testCase.bundle));
  return executor.exec_expression(expression, source);
}

function populationCode(code) {
  return {
    coding: [
      {
        system: 'http://terminology.hl7.org/CodeSystem/measure-population',
        code
      }
    ]
  };
}

async function main() {
  const byExpression = {};
  for (const expression of expressions) {
    byExpression[expression] = (await evaluate(expression)).patientResults;
  }

  const actualByCase = {};
  for (const testCase of testCases) {
    const patientId = testCase.bundle.entry.find(
      entry => entry.resource.resourceType === 'Patient'
    ).resource.id;
    actualByCase[testCase.id] = {};
    for (const expression of expressions) {
      const result = byExpression[expression][patientId];
      assert.ok(result, `${testCase.id}: no CQL result for Patient/${patientId}`);
      actualByCase[testCase.id][expression] = result[expression];
    }
    assert.deepEqual(actualByCase[testCase.id], testCase.expected, testCase.id);
  }

  const results = Object.values(actualByCase);
  const counts = {
    'Initial Population': results.filter(result => result['Initial Population']).length,
    'Denominator 1': results.filter(result => result['Denominator 1']).length,
    'Denominator 1 Exclusion': results.filter(
      result => result['Denominator 1'] && result['Denominator 1 Exclusion']
    ).length,
    'Numerator 1': results.filter(
      result =>
        result['Denominator 1'] &&
        !result['Denominator 1 Exclusion'] &&
        result['Numerator 1']
    ).length
  };
  const actualReport = {
    resourceType: 'MeasureReport',
    id: 'bc-qi-01-synthetic-summary',
    status: 'complete',
    type: 'summary',
    measure:
      'https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qi-01',
    period: { start: '2026-01-01', end: '2026-12-31' },
    group: [
      {
        population: [
          { code: populationCode('initial-population'), count: counts['Initial Population'] },
          { code: populationCode('denominator'), count: counts['Denominator 1'] },
          {
            code: populationCode('denominator-exclusion'),
            count: counts['Denominator 1 Exclusion']
          },
          { code: populationCode('numerator'), count: counts['Numerator 1'] }
        ]
      }
    ]
  };
  assert.deepEqual(actualReport, expectedReport);
  process.stdout.write(
    `${JSON.stringify({ cases: testCases.length, expressions: expressions.length, counts })}\n`
  );
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
