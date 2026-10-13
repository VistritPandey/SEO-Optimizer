import {test} from 'node:test';
import assert from 'node:assert/strict';
import {allowedRequest} from '../lib/proxy-policy.mjs';
test('proxy supports user-facing endpoints with explicit methods', () => {
  for (const [path, method] of [['projects', 'POST'], ['projects/abc-123', 'PATCH'], ['projects/abc/workspace', 'PUT'], ['github/connect', 'DELETE'], ['projects/abc/activity', 'GET']]) assert.equal(allowedRequest(path, method), true);
});
test('proxy refuses secrets, worker capabilities and traversal', () => {
  for (const [path, method] of [['worker/claim', 'POST'], ['projects/a/credentials', 'PUT'], ['../worker/claim', 'POST'], ['projects/%2e%2e', 'GET'], ['projects/a', 'DELETE'], ['github/callback', 'GET'], ['projects/a/activity', 'POST']]) assert.equal(allowedRequest(path, method), false);
});
