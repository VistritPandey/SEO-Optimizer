import { testedPlatform } from "@/lib/platforms";

export function PlatformLogo({
  platform,
  size = 24,
  decorative = true,
}: {
  platform: string;
  size?: number;
  decorative?: boolean;
}) {
  const brand = testedPlatform(platform);
  return (
    <svg
      className="platform-logo"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={brand ? "currentColor" : "none"}
      stroke={brand ? undefined : "currentColor"}
      strokeWidth={brand ? undefined : 1.5}
      aria-hidden={decorative ? true : undefined}
      role={decorative ? undefined : "img"}
      aria-label={decorative ? undefined : brand?.name || "Website platform"}
      focusable="false"
    >
      <path
        d={
          brand?.path ||
          "M9 15l6-6M8 16l-2 2a3 3 0 0 1-4-4l5-5a3 3 0 0 1 4 0M16 8l2-2a3 3 0 0 1 4 4l-5 5a3 3 0 0 1-4 0"
        }
      />
    </svg>
  );
}
