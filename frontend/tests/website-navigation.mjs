import test from "node:test";
import assert from "node:assert/strict";
import {
  selectWebsite,
  websitePath,
  rememberedWebsite,
  rememberWebsite,
} from "../lib/website-navigation.mjs";

test("website pages use the last accessible selection, then the first website", () => {
  const websites = [{ id: "first" }, { id: "last" }];
  assert.equal(selectWebsite(websites, "", "last").id, "last");
  assert.equal(selectWebsite(websites, "", "deleted").id, "first");
  assert.equal(selectWebsite([], "", "last"), undefined);
  assert.equal(selectWebsite(websites, "another-tenant", "last"), undefined);
  assert.equal(selectWebsite(websites, "first", "last").id, "first");
});

test("website routes preserve selection and map audit and settings pages", () => {
  assert.equal(
    websitePath("activity", "website"),
    "/dashboard/audits?project=website",
  );
  assert.equal(
    websitePath("policy", "website"),
    "/dashboard/settings?project=website",
  );
  assert.equal(
    websitePath("connectors", "website"),
    "/dashboard/connections?project=website",
  );
  assert.equal(websitePath("findings"), "/dashboard/findings");
});

test("remembered website selection is identity-scoped and optional", () => {
  const values = new Map();
  const previous = globalThis.localStorage;
  globalThis.localStorage = {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
  };
  try {
    rememberWebsite("one", "website");
    assert.equal(rememberedWebsite("one"), "website");
    assert.equal(rememberedWebsite("two"), "");
    globalThis.localStorage = {
      getItem() {
        throw new Error("disabled");
      },
      setItem() {
        throw new Error("disabled");
      },
    };
    assert.equal(rememberedWebsite("one"), "");
    assert.doesNotThrow(() => rememberWebsite("one", "website"));
  } finally {
    if (previous === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = previous;
  }
});
