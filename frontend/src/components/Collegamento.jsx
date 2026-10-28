import { hrefSicuro } from "../lib/url";

/** A link that only renders as one when the href is http(s); otherwise plain
 *  muted text, so a hostile href from a post never becomes clickable. */
export default function Collegamento({ href, children }) {
  const sicuro = hrefSicuro(href);
  if (!sicuro) return <span className="text-muted">{children}</span>;
  return (
    <a href={sicuro} target="_blank" rel="noreferrer noopener" className="underline">
      {children}
    </a>
  );
}
