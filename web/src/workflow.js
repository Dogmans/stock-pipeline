export const colors = { passed: '#258564', failed: '#c8786e', unavailable: '#c5993f', error: '#aa4c75' };
export const outcomeLabels = { passed: 'Pass', failed: 'Fail', unavailable: 'Unavailable', error: 'Error' };

export function defaultRuleText(catalog, params = {}) {
  const rule = catalog?.default_rule;
  if (!rule) return 'Default rule details unavailable.';
  const override = params[rule.parameter];
  const value = override == null || (rule.zero_uses_default && override === 0) ? rule.value : override;
  return `${rule.metric} ${rule.operator === 'gte' ? '≥' : '≤'} ${value}${rule.unit || ''}`;
}

export function fromDocument(doc) {
  if (doc?.version !== 1 || !Array.isArray(doc.nodes) || !Array.isArray(doc.edges)) throw Error('Choose a version 1 workflow JSON file.');
  return {
    nodes: doc.nodes.map((node, index) => ({ id: node.id, type: 'workflow',
      position: node.position || { x: index * 330, y: 100 },
      data: { kind: node.type, screener: node.screener, params: node.params || {},
        criterion: node.criterion || { operator: 'default' }, label: node.label } })),
    edges: doc.edges.map(e => ({ ...e, sourceHandle: e.sourceHandle || 'passed' })),
  };
}

export function toDocument(name, universe, nodes, edges) {
  return { version: 1, name, universe, nodes: nodes.map(({ id, position, data }) => ({
    id, type: data.kind, position, ...(data.label ? { label: data.label } : {}),
    ...(data.kind === 'screener' ? { screener: data.screener, params: data.params || {}, criterion: data.criterion || { operator: 'default' } } : {}),
  })), edges: edges.map(({ id, source, target, sourceHandle }) => ({ id, source, target, sourceHandle: sourceHandle || 'passed' })) };
}

export function logicKey(document) {
  return JSON.stringify({ universe: document.universe,
    nodes: document.nodes.map(({position, label, ...rest}) => rest).sort((a,b) => a.id.localeCompare(b.id)),
    edges: [...document.edges].sort((a,b) => a.id.localeCompare(b.id)) });
}

export function canConnect(connection, nodes, edges) {
  const { source, target } = connection, port = connection.sourceHandle || 'passed';
  const sourceKind = nodes.find(n => n.id === source)?.data.kind;
  if (source === target || !source || !target) return false;
  if (sourceKind === 'output' || nodes.find(n => n.id === target)?.data.kind === 'universe') return false;
  if (edges.some(e => e.target === target || (sourceKind !== 'universe' && e.source === source && (e.sourceHandle || 'passed') === port))) return false;
  const pending = [target], seen = new Set();
  while (pending.length) {
    const node = pending.pop();
    if (node === source) return false;
    if (seen.has(node)) continue;
    seen.add(node); edges.filter(e => e.source === node).forEach(e => pending.push(e.target));
  }
  return true;
}

export function volumeWidth(count, universeCount) {
  return Math.max(1, (count / Math.max(1, universeCount)) * 48);
}

export function csv(rows) {
  const columns = [...new Set(rows.flatMap(row => Object.keys(row)))];
  const quote = value => {
    let text = value == null ? '' : String(value);
    if (/^[=+@\-]/.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  return [columns, ...rows.map(row => columns.map(key => row[key]))].map(row => row.map(quote).join(',')).join('\r\n');
}
