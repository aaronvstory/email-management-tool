// Cross-platform file walker that ignores Windows ADS like :Zone.Identifier
const fs = require('fs').promises;
const path = require('path');

function isAltDataStream(p) {
  // Match "filename:StreamName" but not "C:\"
  return /:[^\\/]+$/.test(p);
}

async function safeLstat(p) {
  try {
    return await fs.lstat(p);
  } catch (err) {
    // Skip transient ENOENT (common when scanning ADS) instead of crashing
    if (err && err.code === 'ENOENT') return null;
    throw err;
  }
}

async function walk(dir, out = []) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (isAltDataStream(full)) continue; // skip :Zone.Identifier, etc.
    const st = await safeLstat(full);
    if (!st) continue;
    if (st.isDirectory()) {
      await walk(full, out);
    } else {
      out.push(full);
    }
  }
  return out;
}

module.exports = { walk };
