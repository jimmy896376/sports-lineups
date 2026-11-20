import assert from 'node:assert/strict';
import { test } from 'node:test';
import worker from './worker.mjs';

test('stale feed recovers through GitHub API when raw download fails', async () => {
  const oldFetch = globalThis.fetch;
  const values = new Map([['lineup-feed-bridge:bull-feed', JSON.stringify({ asOf: '2026-11-19T00:00:00Z', matches: [{}] })]]);
  const env = { LINEUP_CACHE: {
    get: async key => values.get(key),
    put: async (key, value) => values.set(key, value),
  } };
  const calls = [];
  globalThis.fetch = async url => {
    calls.push(url);
    return url.includes('raw.githubusercontent.com')
      ? new Response('', { status: 403 })
      : new Response(JSON.stringify({ asOf: '2026-11-20T13:00:00Z', matches: [{}] }));
  };
  try {
    const response = await worker.fetch(new Request('https://bridge.example/bull-feed.json'), env);
    assert.equal(response.status, 200);
    assert.equal((await response.json()).asOf, '2026-11-20T13:00:00Z');
    assert.equal(calls.length, 2);
    assert.ok(Number(values.get('lineup-feed-bridge:bull-feed:synced')) > 0);
  } finally {
    globalThis.fetch = oldFetch;
  }
});
