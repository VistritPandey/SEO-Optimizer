import assert from "node:assert/strict";
import { test } from "node:test";
import { execute, revision } from "./bridge.mjs";

test("official SDK bridge reads mapped values and updates only requested CMS fields", async () => {
  const item = { id: "item1", slug: "desk-lamps", fieldData: { seoTitle: {type:"string",value:""}, other:{type:"string",value:"preserved"} },
    async setAttributes({fieldData}) { this.fieldData = {...this.fieldData,...fieldData}; } };
  const api = { async getCollection(id) { assert.equal(id,"collection1"); return { async getItems() { return [item]; } }; } };
  const options = {collection_id:"collection1",seo_title_field:"seoTitle"};
  const [record] = await execute(api,{action:"collect",limit:1},options);
  assert.equal(record.fields.seo_title,"");
  await execute(api,{action:"write",resource_id:"item1",expected_revision:record.revision,changes:{seoTitle:"Desk lamps"}},options);
  assert.equal(item.fieldData.seoTitle.value,"Desk lamps");
  assert.equal(item.fieldData.other.value,"preserved");
  await assert.rejects(execute(api,{action:"write",resource_id:"item1",expected_revision:record.revision,changes:{seoTitle:"Another title"}},options),/Content changed/);
  await assert.rejects(execute(api,{action:"write",resource_id:"item1",expected_revision:revision(item),changes:{other:"unsafe"}},options),/not permitted/);
});
