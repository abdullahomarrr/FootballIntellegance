// Refresh the historical landing snapshot from the project's API.
// Run: node scripts/refresh-landing-evidence.mjs [API_URL]
import { writeFile } from 'node:fs/promises';
const base = process.argv[2] || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:18000';
const paths = { player: '', seasons: '/seasons', metrics: '/metrics', similar: '/similar' };
const entries = await Promise.all(Object.entries(paths).map(async ([key, suffix]) => {
  const response = await fetch(`${base}/players/2376${suffix}`, { signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`${key}: HTTP ${response.status}`);
  return [key, await response.json()];
}));
const snapshot = { captured_at: new Date().toISOString(), ...Object.fromEntries(entries) };
if (snapshot.player.data.canonical_name !== 'Toni Kroos' || snapshot.seasons.data.length !== 1 || snapshot.seasons.data[0].season_label !== '2017/18') throw new Error('The featured identity or season changed; review the landing narrative before refreshing.');
const required = ['passes_per_90', 'key_passes_per_90', 'assists_per_90', 'interceptions_per_90'];
if (!required.every(key => snapshot.metrics.data.some(row => row.metric_name === key && row.percentile != null && row.metric_value != null)) || snapshot.similar.data.length < 3) throw new Error('Incomplete evidence; preserving the previous snapshot.');
await writeFile(new URL('../app/data/landing-evidence.json', import.meta.url), JSON.stringify(snapshot, null, 2) + '\n');
console.log('Refreshed verified historical landing evidence. Review changed values and interpretations before publishing.');
