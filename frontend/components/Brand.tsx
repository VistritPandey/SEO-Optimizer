import Image from "next/image";
import Link from "next/link";

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
        <Image src="/brand/mark.png" width={48} height={48} alt="" preload />
      </span>
      {!compact && <span className="brand-name">Your Optimiser</span>}
    </Link>
  );
}
