import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

export const alt = "Your Optimiser - Your autonomous SEO agent.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const logo = await readFile(join(process.cwd(), "public/brand/logo.png"));
  return new ImageResponse(
    <div
      style={{
        display: "flex",
        width: "100%",
        height: "100%",
        background: "#f7f7f0",
        color: "#242d25",
        padding: "64px 72px",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 15 }}>
        <img
          src={`data:image/png;base64,${logo.toString("base64")}`}
          width={64}
          height={64}
          alt=""
        />
        <span style={{ fontSize: 29, fontWeight: 600, letterSpacing: -1 }}>
          Your Optimiser
        </span>
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          fontSize: 70,
          lineHeight: 1.12,
          letterSpacing: -3,
        }}
      >
        <span>Your autonomous</span>
        <span style={{ color: "#315443" }}>SEO agent.</span>
      </div>
      <div
        style={{
          display: "flex",
          borderTop: "1px solid #dbe0d6",
          paddingTop: 25,
          justifyContent: "space-between",
          color: "#315443",
          fontSize: 18,
        }}
      >
        <span>Ongoing SEO care. Reviewable fixes. Checked results.</span>
        <span>youroptimiser.com</span>
      </div>
    </div>,
    size,
  );
}
