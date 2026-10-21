"use client";

import { useId } from "react";

export function BrandSymbol() {
  const id = useId();
  return (
    <svg className="brand-symbol" viewBox="0 0 96 96" aria-hidden="true">
      <defs>
        {/* Remove the paper background and tint the existing silhouette with the theme colour. */}
        <filter id={id} colorInterpolationFilters="sRGB">
          <feColorMatrix
            in="SourceGraphic"
            type="matrix"
            values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -1 0 0 0 1"
          />
          <feComponentTransfer result="shape">
            <feFuncA type="table" tableValues="0 0 0.4 1 1" />
          </feComponentTransfer>
          <feFlood floodColor="currentColor" />
          <feComposite in2="shape" operator="in" />
        </filter>
      </defs>
      <image
        href="/brand/mark.png"
        width="96"
        height="96"
        filter={`url(#${id})`}
      />
    </svg>
  );
}
