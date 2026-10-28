import { Button } from "@suite/design-system";

/** The instance selector in the bar: «Tutte» plus every registered instance.
 *
 *  An unreachable instance is still listed, marked and with its reason on
 *  hover: hiding it would make a broken instance look like one that was never
 *  there (degradazione nominata, Life spec 2026-10-14 §4.6). */
export default function SceltaIstanza({
  istanze,
  scelta,
  onScegli,
  errore = null,
}) {
  const voci = [
    { id: "", etichetta: "Tutte" },
    ...istanze.map((i) => ({ ...i, etichetta: i.id })),
  ];
  return (
    <div
      role="group"
      aria-label="Istanza Life"
      className="flex flex-wrap items-center gap-1 text-xs"
    >
      {voci.map((v) => {
        const giu = v.status === "unreachable";
        const attiva = scelta === v.id;
        return (
          <Button key={v.id || "tutte"} variant="ghost" size="sm" type="button" aria-pressed={attiva}
            title={giu ? `Irraggiungibile: ${v.reason}` : v.default ? "Default del device" : undefined}
            onClick={() => onScegli(v.id)} className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 transition-colors focus-visible:outline-2 focus-visible:outline-info ${attiva ? "border-info bg-info/15 text-text font-medium" : "border-border text-muted hover:bg-surface-2 hover:text-text"} ${giu ? "border-dashed" : ""}`}>
            {v.etichetta}
            {giu && <span className="text-warning" aria-label="irraggiungibile">⚠</span>}
          </Button>
        );
      })}
      {errore && (
        <span className="text-danger">istanze non lette: {errore}</span>
      )}
    </div>
  );
}
/** Which instance an element belongs to: shown in the «tutte» view only. */
export function BadgeIstanza({ id }) {
  if (!id) return null;
  return (
    <span className="inline-flex items-center rounded-full border border-border bg-surface px-2 py-0.5 text-xs text-muted">
      {id}
    </span>
  );
}
