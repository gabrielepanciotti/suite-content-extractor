import { useState } from "react";
import { Button } from "@suite/design-system";

/** A command to paste in a terminal, with its own copy button. */
export default function Comando({ testo }) {
  const [copiato, setCopiato] = useState(false);
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
    <div className="mt-2 flex items-start gap-2 rounded-lg border border-border bg-surface-2 p-2">
      <pre className="min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap font-mono text-xs">
        {testo}
      </pre>
      <Button size="sm" variant="secondary" onClick={copia}>
        {copiato ? "Copiato" : "Copia"}
      </Button>
    </div>
  );
}
