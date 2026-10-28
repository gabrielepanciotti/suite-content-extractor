import { useState } from "react";
import { Button } from "@suite/design-system";

const SOGLIA_CARATTERI = 200;
const SOGLIA_RIGHE = 3;

/** Text that shows its first lines and a custom «mostra tutto» control.
 *  The control only exists when there is something to reveal: layout is not
 *  measurable here, so «long» is decided on characters and line breaks. */
export default function TestoComprimibile({ testo }) {
  const [aperto, setAperto] = useState(false);
  const lungo = testo.length > SOGLIA_CARATTERI || testo.split("\n").length > SOGLIA_RIGHE;
  return (
    <div>
      <p
        data-testid="testo-comprimibile"
        className={`whitespace-pre-line text-sm ${lungo && !aperto ? "line-clamp-3" : ""}`}
      >
        {testo}
      </p>
      {lungo && (
        <Button
          variant="link"
          size="sm"
          aria-expanded={aperto}
          onClick={() => setAperto((a) => !a)}
          className="mt-1 rounded-button text-xs text-muted underline transition-colors hover:text-text focus-visible:outline-2 focus-visible:outline-info"
        >
          {aperto ? "comprimi" : "mostra tutto"}
        </Button>
      )}
    </div>
  );
}
