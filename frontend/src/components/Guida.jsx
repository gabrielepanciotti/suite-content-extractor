import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@suite/design-system";
import Collegamento from "./Collegamento";

function testoDi(nodo) {
  if (nodo == null || typeof nodo === "boolean") return "";
  if (typeof nodo === "string" || typeof nodo === "number") return String(nodo);
  if (Array.isArray(nodo)) return nodo.map(testoDi).join("");
  return testoDi(nodo.props?.children);
}

/** A code block with its own copy button. */
function BloccoCodice({ children }) {
  const [copiato, setCopiato] = useState(false);
  const testo = testoDi(children).replace(/\n$/, "");
  const copia = async () => {
    try {
      await navigator.clipboard.writeText(testo);
      setCopiato(true);
      setTimeout(() => setCopiato(false), 1500);
    } catch {
      setCopiato(false);
    }
  };
  return (
    <div className="my-2 flex items-start gap-2 rounded-lg border border-border bg-surface-2 p-2">
      <pre className="min-w-0 flex-1 overflow-x-auto font-mono text-xs">{children}</pre>
      <Button size="sm" variant="secondary" onClick={copia}>
        {copiato ? "Copiato" : "Copia"}
      </Button>
    </div>
  );
}

const COMPONENTI = {
  h1: (p) => <h3 className="mt-4 text-base font-semibold first:mt-0" {...strip(p)} />,
  h2: (p) => <h3 className="mt-4 text-base font-semibold first:mt-0" {...strip(p)} />,
  h3: (p) => <h4 className="mt-3 text-sm font-semibold first:mt-0" {...strip(p)} />,
  h4: (p) => <h5 className="mt-3 text-sm font-semibold first:mt-0" {...strip(p)} />,
  p: (p) => <p className="mt-2 text-sm leading-relaxed first:mt-0" {...strip(p)} />,
  ul: (p) => <ul className="mt-2 list-disc pl-5 text-sm" {...strip(p)} />,
  ol: (p) => <ol className="mt-2 list-decimal pl-5 text-sm" {...strip(p)} />,
  li: (p) => <li className="mt-1" {...strip(p)} />,
  blockquote: (p) => <blockquote className="mt-2 border-l-2 border-border pl-3 text-sm text-muted" {...strip(p)} />,
  a: ({ href, children }) => <Collegamento href={href}>{children}</Collegamento>,
  pre: ({ children }) => <BloccoCodice>{children}</BloccoCodice>,
  code: ({ className, children }) => (
    <code className={`font-mono text-xs ${className ? "" : "rounded-md bg-surface-2 px-1 py-0.5"} ${className || ""}`}>
      {children}
    </code>
  ),
  table: (p) => (
    <div className="mt-2 overflow-x-auto">
      <table className="w-full border-collapse text-sm" {...strip(p)} />
    </div>
  ),
  th: (p) => <th className="border border-border bg-surface-2 px-2 py-1 text-left font-semibold" {...strip(p)} />,
  td: (p) => <td className="border border-border px-2 py-1 align-top" {...strip(p)} />,
};

// react-markdown passes the hast `node` along: it must not reach the DOM.
function strip({ node, ...resto }) {
  return resto;
}

/** The guide of a tool, written as markdown in its issue. */
export default function Guida({ testo }) {
  return (
    <div data-testid="guida" className="min-w-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTI}>
        {testo}
      </ReactMarkdown>
    </div>
  );
}
