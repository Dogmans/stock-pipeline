import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultRuleText } from './workflow.js';

test('default rule description follows parameter overrides and constructor fallback', () => {
  const catalog = {default_rule: {metric: 'P/E', operator: 'lte', value: 15, parameter: 'max_pe', zero_uses_default: true}};
  assert.equal(defaultRuleText(catalog), 'P/E ≤ 15');
  assert.equal(defaultRuleText(catalog, {max_pe: 9}), 'P/E ≤ 9');
  assert.equal(defaultRuleText(catalog, {max_pe: 0}), 'P/E ≤ 15');
  catalog.default_rule.zero_uses_default = false;
  assert.equal(defaultRuleText(catalog, {max_pe: 0}), 'P/E ≤ 0');
  assert.equal(defaultRuleText({default_rule: {metric: 'Sentiment score', operator: 'gte', value: 1, unit: ' / 100'}}), 'Sentiment score ≥ 1 / 100');
  assert.equal(defaultRuleText(null), 'Default rule details unavailable.');
});
import { canConnect, csv, fromDocument, logicKey, toDocument, volumeWidth } from './workflow.js';

const doc = { version: 1, name: 'Test', universe: { symbols: ['AAPL'] },
  nodes: [{ id: 'u', type: 'universe', position: {x:0,y:0} }, { id: 's', type: 'screener', screener: 'quality', params: {}, criterion: {operator:'default'}, position: {x:1,y:1} }, { id: 'o', type: 'output', position: {x:2,y:2} }],
  edges: [{ id: 'e', source: 'u', sourceHandle: 'passed', target: 's' }] };

test('workflow round trips and layout does not invalidate scores', () => {
  const graph = fromDocument(doc), restored = toDocument(doc.name, doc.universe, graph.nodes, graph.edges);
  assert.equal(restored.nodes[1].screener, 'quality');
  assert.equal(logicKey(restored), logicKey({...restored, nodes: restored.nodes.map(n => ({...n, position:{x:99,y:99}}))}));
});

test('connections reject duplicate inputs, duplicate outcomes, and cycles', () => {
  const graph = fromDocument(doc);
  assert.equal(canConnect({source:'s', target:'o', sourceHandle:'passed'}, graph.nodes, graph.edges), true);
  const edges = [...graph.edges, {id:'x', source:'s', target:'o', sourceHandle:'passed'}];
  assert.equal(canConnect({source:'u', target:'o', sourceHandle:'passed'}, graph.nodes, edges), false);
  assert.equal(canConnect({source:'s', target:'u', sourceHandle:'failed'}, graph.nodes, edges), false);
  assert.equal(canConnect({source:'s', target:'o', sourceHandle:'passed'}, graph.nodes, edges), false);
});

test('universe can fan out to multiple screeners', () => {
  const graph = fromDocument(doc);
  const nodes = [...graph.nodes, {id:'s2', type:'workflow', data:{kind:'screener'}}];
  assert.equal(canConnect({source:'u', target:'s2', sourceHandle:'passed'}, nodes, graph.edges), true);
});

test('edge width is bounded and CSV protects spreadsheet formulas', () => {
  assert.equal(volumeWidth(0, 100), 1); assert.equal(volumeWidth(100, 100), 48);
  assert.match(csv([{symbol:'=CMD()', score:5}]), /"'=CMD\(\)"/);
});
