const repo = 'jimmy896376/sports-lineups';
const allowed = new Set(['bull-feed.json', 'nude-feed.json', 'projections.json', 'name-catalog.json', 'team-ko.json', 'external-forecasts.json', 'results.json']);
const feedKey = 'lineup-feed-bridge:bull-feed';
const dispatchKey = 'lineup-feed-bridge:refresh-dispatch:last-attempt';
const cacheKey = name => `lineup-feed-bridge:${name}`;
const staleAfterMs = 60 * 60_000;
const dispatchCooldownMs = 30 * 60_000;

async function githubFile(name) {
  const urls = [
    `https://raw.githubusercontent.com/${repo}/main/dist/${name}`,
    `https://api.github.com/repos/${repo}/contents/dist/${name}?ref=main`,
  ];
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

async function dispatchLineupRefresh(env) {
  if (!env.LINEUP_GITHUB_TOKEN) throw Error('Missing LINEUP_GITHUB_TOKEN');
  const lastAttempt = Number(await env.LINEUP_CACHE.get(dispatchKey) || 0);
  if (Date.now() - lastAttempt < dispatchCooldownMs) return false;

  await env.LINEUP_CACHE.put(dispatchKey, String(Date.now()), { expirationTtl: 24 * 60 * 60 });
  const response = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/refresh-lineups.yml/dispatches`, {
    method: 'POST',
    headers: {
      accept: 'application/vnd.github+json',
      authorization: `Bearer ${env.LINEUP_GITHUB_TOKEN}`,
      'content-type': 'application/json',
      'user-agent': 'bulltv24-lineup-feed-bridge',
      'x-github-api-version': '2022-11-28',
    },
    body: JSON.stringify({ ref: 'main' }),
  });
  if (!response.ok) throw Error(`GitHub workflow dispatch: ${response.status}`);
  return true;
}

function feedIsStale(body) {
  if (!body) return true;
  try {
    const asOf = Date.parse(JSON.parse(body).asOf);
    return !Number.isFinite(asOf) || Date.now() - asOf > staleAfterMs;
  } catch {
    return true;
  }
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
      try { await refreshFeed(env); }
      catch (error) { console.error('Lineup bridge refresh failed', error.message); }

      const body = await env.LINEUP_CACHE.get(feedKey);
      if (!feedIsStale(body)) return;
      try {
        const dispatched = await dispatchLineupRefresh(env);
        if (dispatched) console.log('Dispatched stale lineup refresh workflow');
      } catch (error) {
        console.error('Lineup recovery dispatch failed', error.message);
      }
    })());
  },
};
