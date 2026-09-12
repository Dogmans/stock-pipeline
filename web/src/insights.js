import { stockScreeningPath } from './workflow.js';

export const numeric = value => typeof value === 'number' && Number.isFinite(value);
export function ruleFor(node, catalog, savedNode) {
  if (savedNode?.rule) return savedNode.rule;
  if (!node) return null;
  const criterion = node.data.criterion || {operator: 'default'};
  if (criterion.operator !== 'default') return numeric(criterion.value) ? {...criterion, field:'score', metric:'Score'} : null;
  const rule = catalog[node.data.screener]?.default_rule;
  if (!rule) return null;
  const override = node.data.params?.[rule.parameter];
  return {...rule, value: override == null || (rule.zero_uses_default && override === 0) ? rule.value : override,
    upper_value: node.data.params?.[rule.upper_parameter] ?? rule.upper_value,
    field: node.data.screener === 'fifty_two_week_lows' ? 'pct_above_low' : 'score'};
}

export function pathNodes(selection, nodes, edges) {
  const path = [], seen = new Set();
  let id = selection.id;
  while (id && !seen.has(id)) {
    seen.add(id);
    const node = nodes.find(n => n.id === id);
    if (node?.data.kind === 'screener') path.unshift(node);
    id = edges.find(e => e.target === id)?.source;
  }
  return path;
}

// Midrank percentiles handle ties without depending on input order.
export function percentile(value, values, lower = false) {
  const valid = values.filter(numeric);
  if (!numeric(value) || !valid.length) return null;
  if (valid.length === 1) return 50;
  const worse = valid.filter(v => lower ? v > value : v < value).length;
  const equal = valid.filter(v => v === value).length;
  return 100 * (worse + Math.max(0, equal - 1) / 2) / (valid.length - 1);
}

export function rankRows(rows, path, result, catalog, weights = {}) {
  const dimensions = path.map(node => {
    const rule = ruleFor(node, catalog, result?.nodes[node.id]);
    const records = Object.values(result?.nodes[node.id]?.outcomes || {}).flat();
    const values = new Map(records.map(row => [row.symbol, row[rule?.field || 'score']]));
    const sample = rows.map(row => values.get(row.symbol));
    return {node, rule, values, sample, weight: weights[node.id] ?? 1};
  });
  return rows.map(row => {
    const factors = dimensions.map(d => ({id:d.node.id, label:d.node.data.label || catalog[d.node.data.screener]?.label || d.node.data.screener,
      value:d.values.get(row.symbol), weight:d.weight,
      percentile:d.rule ? percentile(d.values.get(row.symbol), d.sample, d.rule.operator === 'lte') : null}));
    const active = factors.filter(f => f.weight > 0), covered = active.filter(f => f.percentile != null);
    // Do not reward incomplete rows by silently reallocating their missing weights.
    const rank = active.length && covered.length === active.length ? covered.reduce((sum,f) => sum + f.percentile*f.weight,0) / active.reduce((sum,f) => sum+f.weight,0) : null;
    return {...row, rank, factors, coverage:`${covered.length}/${active.length}`};
  }).sort((a,b) => (b.rank ?? -1) - (a.rank ?? -1) || a.symbol.localeCompare(b.symbol));
}

export function nearMisses(path, result, catalog, tolerance = 10) {
  return path.flatMap(node => {
    const rule = ruleFor(node, catalog, result?.nodes[node.id]);
    if (!rule || !numeric(rule.value)) return [];
    return (result?.nodes[node.id]?.outcomes.failed || []).flatMap(row => {
      const value = row[rule.field];
      if (!numeric(value)) return [];
      if (rule.operator === 'between' && value >= rule.value && value <= rule.upper_value) return [];
      const threshold = rule.operator === 'between' && value > rule.upper_value ? rule.upper_value : rule.value;
      const gap = rule.operator === 'between' ? Math.abs(value-threshold) : rule.operator === 'gte' ? threshold-value : value-threshold;
      const percent = threshold === 0 ? null : gap / Math.abs(threshold)*100;
      if (gap < 0 || (percent == null ? gap !== 0 : percent > tolerance)) return [];
      return [{...row, nodeId:node.id, label:node.data.label || catalog[node.data.screener]?.label || node.data.screener,
        value, threshold, gap, percent}];
    });
  }).sort((a,b) => (a.percent ?? 0)-(b.percent ?? 0));
}

export function runChanges(current, previous, selection) {
  if (!previous || !current) return [];
  const before = previous.result.nodes[selection.id]?.outcomes[selection.port] || [];
  const after = current.result.nodes[selection.id]?.outcomes[selection.port] || [];
  const oldSymbols = new Set(before.map(r => r.symbol)), newSymbols = new Set(after.map(r => r.symbol));
  return [...after.filter(r => !oldSymbols.has(r.symbol)).map(r => ({...r,change:'Entered'})),
    ...before.filter(r => !newSymbols.has(r.symbol)).map(r => ({...r,change:'Departed'})),
    ...after.filter(r => oldSymbols.has(r.symbol)).map(r => ({...r,change:'Updated'}))].map(row => {
      const explain = snapshot => {
        const graph = snapshot.workflow;
        const nodes = graph.nodes.map(n => ({id:n.id,data:{kind:n.type,screener:n.screener,...n}}));
        return pathNodes(selection,nodes,graph.edges).map(node => {
          const outcomes = snapshot.result.nodes[node.id]?.outcomes || {};
          const entry = Object.entries(outcomes).find(([,rows]) => rows.some(r => r.symbol === row.symbol));
          const record = entry?.[1].find(r => r.symbol === row.symbol);
          return {id:node.id,label:node.data.label || node.data.screener,outcome:entry?.[0] || 'Not evaluated',score:record?.score,reason:record?.reason};
        });
      };
      return {...row,before:explain(previous),after:explain(current)};
    }).filter(row => row.change !== 'Updated' || JSON.stringify(row.before) !== JSON.stringify(row.after));
}

export function peerContext(symbol, selection, nodes, edges, result, catalog) {
  return stockScreeningPath(symbol,selection,nodes,edges,result,catalog).map(step => {
    const node = nodes.find(n => n.id === step.id), rule = ruleFor(node,catalog,result?.nodes[step.id]);
    const sector = step.row.sector;
    const peers = Object.values(result?.nodes[step.id]?.outcomes || {}).flat().filter(r => sector && sector !== 'Unknown' && r.sector === sector && numeric(r[rule?.field]));
    return {...step,sector,peerCount:peers.length,percentile:peers.length >= 2 ? percentile(step.row[rule?.field],peers.map(r => r[rule.field]),rule.operator === 'lte') : null};
  });
}
