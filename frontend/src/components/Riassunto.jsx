/** A colpo d'occhio: cosa propone lo strumento (o gli strumenti) di questo post.
 *
 *  Un elenco puntato e basta, prima delle schede da decidere: chi decide
 *  vuole prima capire cosa gli si chiede, poi leggere i pro e i contro. */
export default function Riassunto({ scheda }) {
  // Un fallimento non e' una proposta: non va elencato fra le cose proposte.
  const pratiche = scheda.pratiche.filter((t) => t.stato !== "failed");
  if (scheda.gruppi.length === 0 && pratiche.length === 0) return null;
  return (
    <section className="mb-4 rounded-lg border border-border p-4">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted">
        Cosa propone
      </h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
        {scheda.gruppi.map((g) => (
          <li key={g.strumento}>
            <span className="font-medium">{g.tip?.titolo || g.strumento}</span>
            {g.utilizzi.length > 0 && (
              <ul className="mt-1 list-[circle] space-y-0.5 pl-5 text-muted">
                {g.utilizzi.map((u) => (
                  <li key={u.id}>{u.titolo}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
        {pratiche.map((t) => (
          <li key={t.id}>{t.titolo}</li>
        ))}
      </ul>
    </section>
  );
}
