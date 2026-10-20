import test from "node:test";
import assert from "node:assert/strict";
import { requestApi } from "../lib/api-request.mjs";

test("read recovers from an HTML gateway failure without parsing it as JSON", async () => {
  let calls = 0;
  const result = await requestApi(
    "account",
    "GET",
    undefined,
    async () => "fixture",
    async () =>
      ++calls === 1
        ? new Response("<h1>Gateway</h1>", { status: 502 })
        : Response.json({ tier: "free" }),
  );
  assert.deepEqual(result, { tier: "free" });
  assert.equal(calls, 2);
});
test("expired identity refreshes once and persistent rejection requires sign-in", async () => {
  const forced = [];
  await assert.rejects(
    requestApi(
      "account",
      "GET",
      undefined,
      async (force) => {
        forced.push(force);
        return "fixture";
      },
      async () => Response.json({ detail: "Unauthorized" }, { status: 401 }),
    ),
    /session has expired/,
  );
  assert.deepEqual(forced, [false, true]);
});
test("uncertain audit submission is not automatically repeated", async () => {
  let calls = 0;
  await assert.rejects(
    requestApi(
      "projects/site/jobs",
      "POST",
      {},
      async () => "fixture",
      async () => {
        calls++;
        throw new TypeError("network");
      },
    ),
    /Check activity/,
  );
  assert.equal(calls, 1);
});
test("HTML success never appears as saved data", async () => {
  await assert.rejects(
    requestApi(
      "account",
      "GET",
      undefined,
      async () => "fixture",
      async () => new Response("<html>"),
    ),
    /unexpected response/,
  );
});
test("validation errors retain actionable server detail without retrying writes", async () => {
  let calls = 0;
  await assert.rejects(
    requestApi(
      "projects",
      "POST",
      {},
      async () => "fixture",
      async () => {
        calls++;
        return Response.json(
          { detail: "Choose a verified repository." },
          { status: 400 },
        );
      },
    ),
    /verified repository/,
  );
  assert.equal(calls, 1);
});
