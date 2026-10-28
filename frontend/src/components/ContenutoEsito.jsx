import { useState } from "react";
import { Button } from "@suite/design-system";
import { fonteLink } from "../lib/url";
import Collegamento from "./Collegamento";
import TestoComprimibile from "./TestoComprimibile";

const giorno = (quando) => (quando ? quando.slice(0, 10) : null);

/** A custom disclosure: closed by default, so the column stays short. */
export function Apribile({ titolo, children, iniziale = false }) {
  const [aperto, setAperto] = useState(iniziale);
  return (
    <div className="mt-3">
      <Button
        variant="ghost"
        size="sm"
        type="button"
        aria-expanded={aperto}
        onClick={() => setAperto((a) => !a)}
        className="flex w-full items-center gap-1 rounded-button text-left text-xs font-semibold uppercase tracking-wide text-muted transition-colors hover:text-text focus-visible:outline-2 focus-visible:outline-info"
      >
        <span
          aria-hidden
          className={`inline-block transition-transform ${aperto ? "rotate-90" : ""}`}
        >
          ▸
        </span>
        {titolo}
      </Button>
      {aperto && <div className="mt-1">{children}</div>}
    </div>
  );
}

function TipTitolo({ t }) {
  const [aperta, setAperta] = useState(false);
  return (
    <li className="text-sm">
      <Button
        variant="link"
        size="sm"
        type="button"
        aria-expanded={aperta}
        onClick={() => setAperta((a) => !a)}
        className="rounded-button text-left underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-info"
      >
        {t.title}
      </Button>
      {aperta && t.body && (
        <div className="mt-1">
          <TestoComprimibile testo={t.body} />
        </div>
      )}
    </li>
  );
}

function Aggiunto({ a }) {
  const quando = giorno(a.quando);
  return (
    <li className="text-sm">
      <span className="text-xs uppercase tracking-wide text-muted">
        {a.tipo}
      </span>{" "}
      {a.url ? (
        <Collegamento href={a.url}>{a.riferimento}</Collegamento>
      ) : (
        <span>{a.riferimento}</span>
      )}
      {quando && <span className="ml-2 text-xs text-muted">{quando}</span>}
    </li>
  );
}

/** What kind of thing a source is, in words a person uses. */
export function tipoFonte(sourceId, url) {
  const s = `${sourceId || ""} ${url || ""}`;
  if (/instagram/.test(s)) return "reel Instagram";
  if (/youtu\.?be/.test(s)) return "video YouTube";
  if (/notion\.(so|site)/.test(s)) return "pagina Notion";
  if ((sourceId || "").startsWith("file:")) return "file caricato";
  if (/^https?:/.test(url || sourceId || "")) return "articolo";
  return "fonte";
}

/** The first tip of the source: what the source said the tool is. */
export const cosaDiceLaFonte = (contenuto = []) =>
  contenuto.flatMap((f) => f.tips || [])[0]?.body || "";

/** The sources a tool came from: links as chips, the tips as titles only,
 *  later additions folded. Short by construction. */
export default function ContenutoEsito({ contenuto = [] }) {
  const aggiunti = contenuto.flatMap((f) => f.aggiunti || []);
  const tips = contenuto.flatMap((f) => f.tips || []);
  if (contenuto.length === 0) {
    return (
      <p className="text-sm text-muted">
        Idea interna, non da un contenuto esterno.
      </p>
    );
  }
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap gap-1">
        {contenuto.map((f) => {
          const href = f.url || fonteLink(f.source_id);
          return (
            <span
              key={f.source_id}
              aria-label={`fonte ${f.source_id}`}
              className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-border bg-surface px-2 py-0.5 text-xs text-text"
            >
              <span className="shrink-0 text-muted">
                {tipoFonte(f.source_id, href)}
              </span>
              <span className="min-w-0 truncate">
                <Collegamento href={href}>{href || f.source_id}</Collegamento>
              </span>
            </span>
          );
        })}
      </div>
      {tips.length > 0 && (
        <Apribile titolo={`Le ${tips.length} tip del contenuto`}>
          <ul className="grid gap-1 pl-4">
            {tips.map((t) => (
              <TipTitolo key={t.id} t={t} />
            ))}
          </ul>
        </Apribile>
      )}
      {aggiunti.length > 0 && (
        <Apribile titolo="Aggiunti dopo">
          <ul className="grid gap-1">
            {aggiunti.map((a, i) => (
              <Aggiunto key={`${a.riferimento}-${i}`} a={a} />
            ))}
          </ul>
        </Apribile>
      )}
    </div>
  );
}
