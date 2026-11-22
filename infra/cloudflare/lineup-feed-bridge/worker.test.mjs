import assert from 'node:assert/strict';
import { test } from 'node:test';
import worker, { ensureFreshCollection } from './worker.mjs';

test('lineup feed reads the current GitHub API before a stale raw mirror', async () => {
  const oldFetch = globalThis.fetch;
  const values = new Map([['lineup-feed-bridge:bull-feed', JSON.stringify({ asOf: '2026-11-19T00:00:00Z', matches: [{}] })]]);
  const env = { LINEUP_CACHE: {
    get: async key => values.get(key),
    put: async (key, value) => values.set(key, value),
  } };
  const calls = [];
  globalThis.fetch = async url => {
    calls.push(url);
    return new Response(JSON.stringify({ asOf: url.includes('api.github.com')
      ? '2026-11-20T13:00:00Z' : '2026-11-19T00:00:00Z', matches: [{}] }));
  };
  try {
    const response = await worker.fetch(new Request('https://bridge.example/bull-feed.json'), env);
    assert.equal(response.status, 200);
    assert.equal((await response.json()).asOf, '2026-11-20T13:00:00Z');
    assert.equal(calls.length, 1);
    assert.match(calls[0], /api\.github\.com/);
    assert.match(calls[0], /[?&]v=\d+/);
    assert.ok(Number(values.get('lineup-feed-bridge:bull-feed:synced')) > 0);
  } finally {
    globalThis.fetch = oldFetch;
  }
});

test('lineup feed falls back to raw file when GitHub API fails', async () => {
  const oldFetch = globalThis.fetch;
  const values = new Map();
  const env = { LINEUP_CACHE: {
    get: async key => values.get(key),
    put: async (key, value) => values.set(key, value),
  } };
  const calls = [];
  globalThis.fetch = async url => {
    calls.push(url);
    return url.includes('api.github.com')
      ? new Response('', { status: 503 })
      : new Response(JSON.stringify({ asOf: '2026-11-20T13:00:00Z', matches: [{}] }));
  };
  try {
    const response = await worker.fetch(new Request('https://bridge.example/bull-feed.json'), env);
    assert.equal(response.status, 200);
    assert.equal((await response.json()).asOf, '2026-11-20T13:00:00Z');
    assert.equal(calls.length, 2);
    assert.match(calls[1], /[?&]v=\d+/);
  } finally {
    globalThis.fetch = oldFetch;
  }
});

test('stale published feed dispatches one collection run per 20 minutes', async () => {
  const oldFetch = globalThis.fetch;
  const values = new Map();
  const now = Date.parse('2026-11-22T14:00:00Z');
  const env = {
    LINEUP_GITHUB_TOKEN: 'github_pat_testtoken',
    LINEUP_CACHE: {
      get: async key => values.get(key),
      put: async (key, value) => values.set(key, value),
    },
  };
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(null, { status: 204 });
  };
  try {
    const stale = JSON.stringify({ asOf: '2026-11-22T13:30:00Z', matches: [{}] });
    assert.equal(await ensureFreshCollection(env, stale, now), true);
    assert.equal(await ensureFreshCollection(env, stale, now + 5 * 60_000), false);
    assert.equal(calls.length, 1);
    assert.match(calls[0].url, /refresh-lineups\.yml\/dispatches$/);
    assert.equal(JSON.parse(calls[0].options.body).ref, 'main');
    assert.equal(await ensureFreshCollection(env, stale, now + 21 * 60_000), true);
    assert.equal(calls.length, 2);
  } finally {
    globalThis.fetch = oldFetch;
  }
});

test('fresh feed never dispatches collection', async () => {
  const env = { LINEUP_CACHE: { get: async () => undefined } };
  assert.equal(await ensureFreshCollection(env, JSON.stringify({ asOf: '2026-11-22T13:50:00Z' }), Date.parse('2026-11-22T14:00:00Z')), false);
});

test('failed dispatch does not block the next retry', async () => {
  const oldFetch = globalThis.fetch;
  const values = new Map();
  const env = {
    LINEUP_GITHUB_TOKEN: 'github_pat_testtoken',
    LINEUP_CACHE: {
      get: async key => values.get(key),
      put: async (key, value) => values.set(key, value),
    },
  };
  globalThis.fetch = async () => new Response('', { status: 503 });
  try {
    await assert.rejects(ensureFreshCollection(env, JSON.stringify({ asOf: '2026-11-22T13:30:00Z' }), Date.parse('2026-11-22T14:00:00Z')), /HTTP 503/);
    assert.equal(values.has('lineup-feed-bridge:refresh-dispatched'), false);
  } finally {
    globalThis.fetch = oldFetch;
  }
});

test('invalid token is rejected before building an Authorization header', async () => {
  const env = {
    LINEUP_GITHUB_TOKEN: '잘못된 값',
    LINEUP_CACHE: { get: async () => undefined },
  };
  await assert.rejects(
    ensureFreshCollection(env, JSON.stringify({ asOf: '2026-11-22T13:30:00Z' }), Date.parse('2026-11-22T14:00:00Z')),
    /Invalid GitHub workflow token format/,
  );
});
