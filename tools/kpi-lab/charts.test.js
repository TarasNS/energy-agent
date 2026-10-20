'use strict';
const assert = require('node:assert');
const { renderChart } = require('./charts.js');

let passed = 0;
function test(name, fn) {
  fn();
  passed += 1;
  console.log('ok - ' + name);
}

function chart(kind, series) {
  return { id: 'c1', kind, title: 'Energy lost', series };
}

const data = [
  { name: 'Park A', points: [{ x: 'Jun 1', y: '85.00' }, { x: 'Jun 2', y: '0.50' }, { x: 'Jun 3', y: '120.25' }] },
];

for (const kind of ['line', 'bar', 'area', 'table']) {
  test(kind + ': renders title and every y verbatim', () => {
    const out = renderChart(chart(kind, data));
    assert.strictEqual(typeof out, 'string');
    assert.ok(out.includes('Energy lost'));
    for (const y of ['85.00', '0.50', '120.25']) assert.ok(out.includes(y), 'missing ' + y);
    assert.ok(!/NaN|undefined/.test(out));
  });

  test(kind + ': empty series does not throw and says no data', () => {
    assert.ok(/No data/.test(renderChart(chart(kind, []))));
    assert.ok(/No data/.test(renderChart(chart(kind, [{ name: 'Park A', points: [] }]))));
  });

  test(kind + ': negative value printed verbatim, no NaN', () => {
    const out = renderChart(chart(kind, [
      { name: 'Park A', points: [{ x: 'a', y: '-12.50' }, { x: 'b', y: '30.00' }] },
    ]));
    assert.ok(out.includes('-12.50'));
    assert.ok(out.includes('30.00'));
    assert.ok(!/NaN|Infinity/.test(out));
  });
}

test('shapes: line/area path, bar rects, table element', () => {
  assert.ok(/<(path|polyline)\b/.test(renderChart(chart('line', data))));
  assert.ok(/<path\b/.test(renderChart(chart('area', data))));
  assert.strictEqual((renderChart(chart('bar', data)).match(/<rect\b/g) || []).length >= 3, true);
  assert.ok(renderChart(chart('table', data)).includes('<table'));
});

test('never invents a number (no sum or average shown)', () => {
  const out = renderChart(chart('table', data));
  for (const bad of ['205.75', '68.58', '68.583', '205.8']) assert.ok(!out.includes(bad));
});

test('escapes html in title, series name and x', () => {
  const out = renderChart({
    id: 'x', kind: 'line', title: '<script>alert(1)</script>',
    series: [{ name: '<b>n</b>', points: [{ x: '<i>', y: '1.00' }] }],
  });
  assert.ok(!out.includes('<script>'));
  assert.ok(!out.includes('<b>n</b>'));
  assert.ok(!out.includes('<i>'));
});

test('unknown kind throws', () => {
  assert.throws(() => renderChart(chart('pie', data)), /Unknown chart kind/);
});

console.log(passed + ' tests passed');
