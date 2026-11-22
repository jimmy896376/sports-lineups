const repo = 'jimmy896376/sports-lineups';
const allowed = new Set(['bull-feed.json', 'nude-feed.json', 'projections.json', 'name-catalog.json', 'team-ko.json', 'external-forecasts.json', 'results.json']);
const feedKey = 'lineup-feed-bridge:bull-feed';
const cacheKey = name => `lineup-feed-bridge:${name}`;
const dispatchKey = 'lineup-feed-bridge:refresh-dispatched';

async function githubFile(name) {
  const raw = `https://raw.githubusercontent.com/${repo}/main/dist/${name}`;
  const api = `https://api.github.com/repos/${repo}/contents/dist/${name}?ref=main`;
  const urls = name === 'bull-feed.json' ? [api, raw] : [raw, api];
  let failure;
  for (const url of urls) {
    try {
      const response = await fetch(url, {
        headers: { accept: 'application/vnd.github.raw+json', 'user-agent': 'bulltv24-lineup-feed-bridge' },
      });
      if (!response.ok) throw Error(`GitHub ${name}: ${response.status}`);
      const body = await response.text();
      JSON.parse(body);
      return body;
    } catch (error) {
      failure = error;
    }
  }
  throw failure;
}

export async function refreshFeed(env) {
  const body = await githubFile('bull-feed.json');
  const next = JSON.parse(body);
  if (!Array.isArray(next.matches) || !next.matches.length || !Number.isFinite(Date.parse(next.asOf)))
    throw Error('Invalid lineup feed');
  const current = await env.LINEUP_CACHE.get(feedKey);
  if (current && Date.parse(JSON.parse(current).asOf) > Date.parse(next.asOf))
    throw Error('Refusing older lineup feed');
  await env.LINEUP_CACHE.put(feedKey, body);
  await env.LINEUP_CACHE.put(`${feedKey}:synced`, String(Date.now()));
  return body;
}

export async function ensureFreshCollection(env, body, now = Date.now()) {
  const age = now - Date.parse(JSON.parse(body).asOf);
  if (age <= 20 * 60_000) return false;
  const last = Number(await env.LINEUP_CACHE.get(dispatchKey) || 0);
  if (now - last < 20 * 60_000) return false;
  if (!env.LINEUP_GITHUB_TOKEN) throw Error('Missing GitHub workflow token');
  if (!/^github_pat_[A-Za-z0-9_]+$/.test(env.LINEUP_GITHUB_TOKEN))
    throw Error('Invalid GitHub workflow token format');
  const response = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/refresh-lineups.yml/dispatches`, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${env.LINEUP_GITHUB_TOKEN}`,
      accept: 'application/vnd.github+json',
      'content-type': 'application/json',
      'user-agent': 'bulltv24-lineup-feed-bridge',
    },
    body: JSON.stringify({ ref: 'main' }),
  });
  if (response.status !== 204) throw Error(`GitHub lineup refresh: HTTP ${response.status}`);
  await env.LINEUP_CACHE.put(dispatchKey, String(now));
  return true;
}

export default {
  async fetch(request, env) {
    const name = new URL(request.url).pathname.slice(1);
    if (request.method !== 'GET' || !allowed.has(name)) return new Response('Not found', { status: 404 });
    try {
      const key = name === 'bull-feed.json' || name === 'nude-feed.json' ? feedKey : cacheKey(name);
      let body = await env.LINEUP_CACHE.get(key);
      if (key === feedKey && (!body || Date.now() - Number(await env.LINEUP_CACHE.get(`${feedKey}:synced`) || 0) > 15 * 60_000)) {
        try { body = await refreshFeed(env); }
        catch (error) {
          if (!body) throw error;
          console.error('Lineup bridge refresh failed', error.message);
        }
      } else if (key !== feedKey && (!body || Date.now() - Date.parse(JSON.parse(body).cachedAt || 0) > 15 * 60_000)) {
        const value = await githubFile(name);
        body = JSON.stringify({ cachedAt: new Date().toISOString(), value: JSON.parse(value) });
        await env.LINEUP_CACHE.put(key, body);
      }
      if (key !== feedKey) body = JSON.stringify(JSON.parse(body).value);
      return new Response(body, { headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'public, max-age=30' } });
    } catch (error) {
      console.error('Lineup bridge fetch failed', error.message);
      return new Response('Upstream unavailable', { status: 502 });
    }
  },
  async scheduled(_event, env, ctx) {
    ctx.waitUntil((async () => {
      let body;
      try { body = await refreshFeed(env); }
      catch (error) {
        body = await env.LINEUP_CACHE.get(feedKey);
        if (!body) throw error;
        console.error('Lineup bridge refresh failed', error.message);
      }
      await ensureFreshCollection(env, body);
    })());
  },
};
