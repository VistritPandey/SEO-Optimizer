import Image from "next/image";
import Link from "next/link";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link className="brand" href="/" aria-label="Your Optimiser home">
      <span className="brand-mark" aria-hidden="true">
        <Image src="/brand/mark.png" width={48} height={48} alt="" preload />
      </span>
      {!compact && <span className="brand-name">Your Optimiser</span>}
    </Link>
  );
}
