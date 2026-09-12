import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultRuleText, stockScreeningPath } from './workflow.js';
import {percentile, rankRows, nearMisses, ruleFor, runChanges, peerContext} from './insights.js';

test('percentile ranking respects direction, ties and missing active factors', () => {
  assert.equal(percentile(10,[10,20,30],true),100);
  assert.equal(percentile(20,[10,20,20,30]),50);
  assert.equal(percentile(10,[10]),50);
  const path = [{id:'s',data:{kind:'screener',screener:'pe',criterion:{operator:'lte',value:20}}}];
  const result = {nodes:{s:{outcomes:{passed:[{symbol:'A',score:10},{symbol:'B',score:15}],unavailable:[{symbol:'C'}]}}}};
  const ranked = rankRows([{symbol:'A'},{symbol:'B'},{symbol:'C'}],path,result,{});
  assert.equal(ranked[0].symbol,'A');
  assert.equal(ranked[0].rank,100);
  assert.equal(ranked[2].rank,null);
  assert.equal(ranked[2].coverage,'0/1');
  assert.equal(rankRows([{symbol:'A'}],path,result,{}, {s:0})[0].rank,null);
});

test('near misses use the threshold metric rather than the inverted 52-week-low score', () => {
  const node = {id:'s',data:{kind:'screener',screener:'fifty_two_week_lows',criterion:{operator:'default'}}};
  const catalog = {fifty_two_week_lows:{default_rule:{metric:'Distance',operator:'lte',value:20}}};
  const result = {nodes:{s:{outcomes:{failed:[{symbol:'A',score:80,pct_above_low:21},{symbol:'B',score:99,pct_above_low:30},{symbol:'C',score:5}]}}}};
  assert.equal(ruleFor(node,catalog).field,'pct_above_low');
  assert.equal(ruleFor(node,catalog,{rule:{field:'pct_above_low',value:18,operator:'lte'}}).value,18);
  const misses = nearMisses([node],result,catalog,10);
  assert.equal(misses.length,1);
  assert.equal(misses[0].symbol,'A');
  assert.equal(misses[0].percent,5);
});

test('run differences include entrants, departures and updated retained stocks', () => {
  const workflow = {nodes:[{id:'s',type:'screener',screener:'quality'},{id:'o',type:'output'}],edges:[{source:'s',target:'o'}]};
  const make = rows => ({workflow,result:{nodes:{o:{outcomes:{passed:rows}},s:{outcomes:{passed:rows}}}}});
  const before = make([{symbol:'A',score:10},{symbol:'B',score:20}]);
  const after = make([{symbol:'B',score:21},{symbol:'C',score:30}]);
  const changes = runChanges(after,before,{id:'o',port:'passed'});
  assert.deepEqual(changes.map(r => [r.symbol,r.change]),[['C','Entered'],['A','Departed'],['B','Updated']]);
  assert.equal(changes[2].before[0].score,20);
  assert.equal(changes[2].after[0].score,21);
});

test('sector comparisons require a known sector and exclude other sectors', () => {
  const node = {id:'s',data:{kind:'screener',screener:'quality',criterion:{operator:'gte',value:1}}};
  const result = {nodes:{s:{outcomes:{passed:[{symbol:'A',sector:'Tech',score:10},{symbol:'B',sector:'Tech',score:20},{symbol:'C',sector:'Energy',score:30}]}}}};
  const step = peerContext('A',{id:'s',port:'passed'},[node],[],result,{})[0];
  assert.equal(step.peerCount,2);
  assert.equal(step.percentile,0);
  assert.equal(peerContext('C',{id:'s',port:'passed'},[node],[],result,{})[0].percentile,null);
});

test('stock explanation follows the selected branch in execution order with its actual outcomes', () => {
  const nodes = [
    {id:'u', data:{kind:'universe'}},
    {id:'a', data:{kind:'screener', screener:'pe', params:{max_pe:12}, criterion:{operator:'default'}}},
    {id:'b', data:{kind:'screener', screener:'quality', criterion:{operator:'gte', value:7}}},
    {id:'other', data:{kind:'screener', screener:'unrelated'}},
    {id:'o', data:{kind:'output'}},
  ];
  const edges = [{source:'u',target:'a'}, {source:'a',target:'b',sourceHandle:'failed'}, {source:'b',target:'o',sourceHandle:'unavailable'}, {source:'u',target:'other'}];
  const result = {nodes:{a:{outcomes:{failed:[{symbol:'ABC',score:19,reason:'Too expensive'}]}}, b:{outcomes:{unavailable:[{symbol:'ABC',reason:'Missing financials'}]}}}};
  const catalog = {pe:{label:'P/E',default_rule:{metric:'P/E',operator:'lte',value:15,parameter:'max_pe'}}};
  const steps = stockScreeningPath('ABC',{id:'o',port:'passed'},nodes,edges,result,catalog);
  assert.deepEqual(steps.map(s => s.id), ['a','b']);
  assert.deepEqual(steps.map(s => s.outcome), ['failed','unavailable']);
  assert.equal(steps[0].rule,'P/E ≤ 12');
  assert.equal(steps[0].row.score,19);
  assert.equal(steps[1].rule,'Score ≥ 7');
  assert.equal(steps[1].row.reason,'Missing financials');
  assert.deepEqual(stockScreeningPath('ABC',{id:'o',port:'passed'},nodes,edges,null,catalog),[]);
  assert.deepEqual(stockScreeningPath('ABC',{id:'u',port:'passed'},nodes,edges,result,catalog),[]);
  const selected = stockScreeningPath('ABC',{id:'a',port:'failed'},nodes,edges,result,catalog);
  assert.equal(selected.length,1);
  assert.equal(selected[0].outcome,'failed');
  assert.equal(stockScreeningPath('UNKNOWN',{id:'a',port:'passed'},nodes,edges,result,catalog)[0].outcome,'unavailable');
});

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

test('price change ranges preserve both bounds and find misses on either side', () => {
  const catalog = {price_change:{default_rule:{metric:'Price change',operator:'between',value:0,upper_value:100,parameter:'min_change',upper_parameter:'max_change',unit:'%'}}};
  const node = {id:'s',data:{screener:'price_change',params:{min_change:10,max_change:20}}};
  assert.equal(defaultRuleText(catalog.price_change,node.data.params),'Price change 10% to 20% (inclusive)');
  assert.equal(ruleFor(node,catalog).upper_value,20);
  const result = {nodes:{s:{outcomes:{failed:[{symbol:'A',score:9.5},{symbol:'B',score:21},{symbol:'C',score:15},{symbol:'D',score:40}]}}}};
  const misses=nearMisses([node],result,catalog);
  assert.deepEqual(misses.map(r=>r.symbol),['A','B']);
  assert.deepEqual(misses.map(r=>r.threshold),[10,20]);
});
