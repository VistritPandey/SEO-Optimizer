import { connect } from "framer-api";
import { createHash } from "node:crypto";

export function revision(item) {
  return createHash("sha256").update(JSON.stringify(item.fieldData)).digest("hex");
}
export async function execute(framer, request, options) {
  const collection = await framer.getCollection(options.collection_id);
  if (!collection) throw new Error("Collection unavailable");
  const items = await collection.getItems();
  const selected = request.resource_id
    ? items.filter((item) => item.id === request.resource_id)
    : items.slice(0, Math.min(request.limit || 50, 100));
  if (request.resource_id && selected.length !== 1) throw new Error("Item unavailable");
  if (request.action === "write") {
    const item = selected[0];
    if (revision(item) !== request.expected_revision) throw new Error("Content changed");
    const allowed = [options.seo_title_field, options.seo_description_field].filter(Boolean);
    const fields = {};
    for (const [key, value] of Object.entries(request.changes)) {
      if (!allowed.includes(key) || typeof value !== "string" || value.length > 20000)
        throw new Error("Field not permitted");
      const existing = item.fieldData[key];
      if (existing && existing.type !== "string") throw new Error("Field must be a string");
      fields[key] = { type: "string", value };
    }
    await item.setAttributes({ fieldData: fields });
    return [];
  }
  return selected.map((item) => ({
    id: item.id, kind: "cms_item", revision: revision(item),
    fields: {
      title: "",
      seo_title: item.fieldData[options.seo_title_field]?.value || "",
      seo_description: item.fieldData[options.seo_description_field]?.value || "",
    },
  }));
}

if (import.meta.url === new URL(process.argv[1], "file:").href) {
  let framer;
  try {
    let input = "";
    for await (const chunk of process.stdin) {
      input += chunk;
      if (input.length > 100000) throw new Error("Input limit");
    }
    const { connection, request } = JSON.parse(input);
    framer = await connect(connection.resource, connection.credentials.access_token);
    const result = await execute(framer, request, connection.options);
    const output = JSON.stringify(result);
    if (output.length > 2000000) throw new Error("Output limit");
    process.stdout.write(output);
  } catch {
    process.stderr.write("Framer operation failed; verify access, collection and current revision.\n");
    process.exitCode = 1;
  } finally {
    if (framer) await framer.disconnect();
  }
}
