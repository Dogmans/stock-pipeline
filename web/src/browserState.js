export function readLocal(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return value && typeof value === 'object' && !Array.isArray(value) ? value : fallback;
  } catch {return fallback;}
}

export function saveLocal(key, value) {
  try {localStorage.setItem(key, JSON.stringify(value));return true;}
  catch {return false;}
}

export function download(name, content, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const link = document.createElement('a');
  link.href = url;link.download = name;link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function exportCsv(name, rows) {
  const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  download(name, rows.map(row => row.map(quote).join(',')).join('\r\n'), 'text/csv;charset=utf-8');
}
