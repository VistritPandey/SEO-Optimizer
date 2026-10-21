import Link from "next/link";
import { BrandSymbol } from "./BrandSymbol";

export function Brand({
  compact = false,
  href = "/",
  label = "Your Optimiser home",
  onClick,
}: {
  compact?: boolean;
  href?: string;
  label?: string;
  onClick?: React.MouseEventHandler<HTMLAnchorElement>;
}) {
  return (
    <Link className="brand" href={href} aria-label={label} onClick={onClick}>
      <span className="brand-mark" aria-hidden="true">
        <BrandSymbol />
      </span>
      {!compact && <span className="brand-name">Your Optimiser</span>}
    </Link>
  );
}
