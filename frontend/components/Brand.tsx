import Image from "next/image";
import Link from "next/link";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link className="brand" href="/" aria-label="Your Optimiser home">
      <Image src="/brand/mark.png" width={40} height={40} alt="" priority />
      {!compact && <span>Your Optimiser</span>}
    </Link>
  );
}
