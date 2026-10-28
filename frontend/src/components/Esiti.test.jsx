import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Esiti from "./Esiti";

const rec = (id, over = {}) => ({
  id, strumento: `S-${id}`, stato: "portato", sintesi: `sintesi ${id}`,
  dove: [`Life: ${id}.py`], come_si_usa: "usalo", comando: null,
  issue: [`https://github.com/o/r/issues/${id.length}`], issue_stato: "closed",
  unito_in: null, commit: [], proposte: [], fonti: ["instagram:AbC"],
  aggiornato: "2026-10-15", ...over,
});

const contenuto = (over = {}) => [{
  source_id: "instagram:AbC", url: "https://www.instagram.com/p/AbC/",
  tips: [{ id: "t1", title: "Tip uno", body: "corpo breve" }], aggiunti: [], ...over,
}];

const DATI = [
  rec("alfa", { comando: "python -m alfa --x", contenuto: contenuto() }),
  rec("beta", { stato: "scartato", dove: ["Nodo: gamma.py"] }),
  rec("delta", { stato: "unito", unito_in: "https://github.com/o/r/pull/9" }),
];

const finto = (dati, extra = {}) => {
  globalThis.fetch = vi.fn((url, opts) => {
    if (opts?.method === "POST") {
      return Promise.resolve({ ok: true, json: async () => extra.sync });
    }
    if (url === "/api/esiti/anomalie") {
      if (extra.erroreAnomalie) {
        return Promise.resolve({ ok: false, statusText: "giù", json: async () => ({}) });
      }
      return Promise.resolve({ ok: true, json: async () => extra.anomalie || [] });
    }
    return Promise.resolve({ ok: true, json: async () => dati });
  });
};

afterEach(() => vi.restoreAllMocks());

const apri = (nome) => fireEvent.click(screen.getByRole("button", { name: new RegExp(nome) }));

beforeEach(() => { window.location.hash = "#/esiti"; });

test("l'intestazione è sempre visibile e il dettaglio è chiuso di default", async () => {
  finto(DATI);
  render(<Esiti />);
  expect(await screen.findByText("S-alfa")).toBeDefined();
  expect(screen.getByText("S-beta")).toBeDefined();
  expect(screen.getByText("sintesi alfa")).toBeDefined();
  expect(screen.queryByText("Storia")).toBeNull();
  const intest = screen.getByRole("button", { name: /S-alfa/ });
  expect(intest.getAttribute("aria-expanded")).toBe("false");
  fireEvent.click(intest);
  expect(intest.getAttribute("aria-expanded")).toBe("true");
  expect(screen.getAllByText("Storia")).toHaveLength(1);
  expect(window.location.hash).toBe("#/esiti/alfa");
  fireEvent.click(intest);
  expect(screen.queryByText("Storia")).toBeNull();
  expect(window.location.hash).toBe("#/esiti");
});

test("Apri tutti e Chiudi tutti", async () => {
  finto(DATI);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  fireEvent.click(screen.getByRole("button", { name: "Apri tutti" }));
  expect(screen.getAllByText("Storia")).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", { name: "Chiudi tutti" }));
  expect(screen.queryByText("Storia")).toBeNull();
});

test("un link con l'hash apre dritto lo strumento", async () => {
  window.location.hash = "#/esiti/beta";
  finto(DATI);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  expect(screen.getAllByText("Storia")).toHaveLength(1);
  expect(screen.getByRole("button", { name: /S-beta/ }).getAttribute("aria-expanded")).toBe("true");
});

test("aperto: issue e fonte come link, cosa fa a sinistra e storia a destra", async () => {
  finto(DATI);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  fireEvent.click(screen.getByRole("button", { name: "Apri tutti" }));
  expect(screen.getAllByText("r#4")[0].closest("a").href).toBe("https://github.com/o/r/issues/4");
  expect(screen.getByText("https://www.instagram.com/p/AbC/").closest("a").href)
    .toBe("https://www.instagram.com/p/AbC/");
  expect(screen.getByText("unito in r#9").closest("a").href).toBe("https://github.com/o/r/pull/9");
  const riga = screen.getByText("S-alfa").closest("article");
  const colonne = riga.querySelector(".md\\:grid-cols-5");
  const [sinistra, destra] = colonne.children;
  expect(sinistra.textContent).toContain("A cosa serve");
  expect(sinistra.textContent).toContain("python -m alfa --x");
  expect(destra.textContent).toContain("Storia");
  expect(destra.textContent).toContain("reel Instagram");
  expect(destra.textContent).not.toContain("python -m alfa");
});

test("la guida è resa come markdown, con copia sui blocchi di codice", async () => {
  const scrivi = vi.fn().mockResolvedValue();
  Object.defineProperty(navigator, "clipboard", { value: { writeText: scrivi }, configurable: true });
  finto([rec("alfa", { comando: null, guida: "## Quando usarlo\n\n- passo **uno**\n\n```bash\nalfa --x\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |" })]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  apri("S-alfa");
  expect(screen.getByRole("heading", { name: "Quando usarlo" })).toBeDefined();
  expect(screen.getByText("uno").tagName).toBe("STRONG");
  expect(screen.getByRole("table")).toBeDefined();
  expect(screen.queryByText("Guida non ancora scritta.")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Copia" }));
  expect(scrivi).toHaveBeenCalledWith("alfa --x");
});

test("senza guida mostra come_si_usa e un avviso tenue", async () => {
  finto([rec("alfa")]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  apri("S-alfa");
  expect(screen.getByText("usalo")).toBeDefined();
  expect(screen.getByText("Guida non ancora scritta.")).toBeDefined();
});

test("le tip compaiono solo come titoli, il testo si apre al click", async () => {
  finto([rec("alfa", { contenuto: contenuto({ tips: [
    { id: "t1", title: "Tip uno", body: "corpo uno" },
    { id: "t2", title: "Tip due", body: "corpo due" },
  ] }) })]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  apri("S-alfa");
  expect(screen.queryByText("Tip uno")).toBeNull();
  expect(screen.getByTestId("idea").className).toContain("line-clamp-4");
  expect(screen.getByTestId("idea").textContent).toBe("corpo uno");
  fireEvent.click(screen.getByRole("button", { name: /Le 2 tip del contenuto/ }));
  expect(screen.getByText("Tip uno")).toBeDefined();
  expect(screen.getAllByText("corpo uno")).toHaveLength(1);
  fireEvent.click(screen.getByText("Tip due"));
  expect(screen.getByText("corpo due")).toBeDefined();
});

test("il testo lungo di una tip si comprime e si espande col controllo custom", async () => {
  const lungo = "riga di testo molto lunga ".repeat(20);
  finto([rec("alfa", { contenuto: contenuto({ tips: [{ id: "t", title: "T", body: lungo }] }) })]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  apri("S-alfa");
  fireEvent.click(screen.getByRole("button", { name: /Le 1 tip/ }));
  fireEvent.click(screen.getByRole("button", { name: "T" }));
  const testo = screen.getByTestId("testo-comprimibile");
  expect(testo.className).toContain("line-clamp-3");
  fireEvent.click(screen.getByRole("button", { name: "mostra tutto" }));
  expect(testo.className).not.toContain("line-clamp-3");
});

test("gli aggiunti dopo sono chiusi di default e compaiono solo se ci sono", async () => {
  finto([
    rec("alfa", { contenuto: contenuto({ aggiunti: [
      { tipo: "link", riferimento: "https://x.test/cheat", url: "https://x.test/cheat", quando: "2026-10-01T10:00:00+00:00" },
      { tipo: "file", riferimento: "guida.pdf", url: null, quando: null },
    ] }) }),
    rec("beta"),
  ]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  fireEvent.click(screen.getByRole("button", { name: "Apri tutti" }));
  expect(screen.getAllByRole("button", { name: /Aggiunti dopo/ })).toHaveLength(1);
  expect(screen.queryByText("guida.pdf")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /Aggiunti dopo/ }));
  expect(screen.getByText("https://x.test/cheat").closest("a").href).toBe("https://x.test/cheat");
  expect(screen.getByText("guida.pdf").closest("a")).toBeNull();
  expect(screen.getByText("2026-10-01")).toBeDefined();
});

test("il banner rosso elenca le anomalie, e non c'è se non ce ne sono", async () => {
  finto(DATI, { anomalie: [
    { tipo: "adottata_senza_issue", riferimento: "p1", messaggio: "«Mai creata» è adottata ma nessuna issue la copre" },
    { tipo: "chiusa_senza_esito", riferimento: "x", messaggio: "X: l'issue è chiusa ma l'esito è ancora «aperto»" },
  ] });
  const { unmount } = render(<Esiti />);
  const banner = await screen.findByRole("alert");
  expect(banner.textContent).toContain("2 anomalie");
  expect(banner.textContent).toContain("«Mai creata» è adottata ma nessuna issue la copre");
  expect(banner.textContent).toContain("X: l'issue è chiusa");
  unmount();
  finto(DATI);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  expect(screen.queryByRole("alert")).toBeNull();
});

test("se il controllo delle anomalie fallisce lo dice, senza nascondere l'elenco", async () => {
  finto(DATI, { erroreAnomalie: true });
  render(<Esiti />);
  expect(await screen.findByText(/Non riesco a controllare le anomalie: giù/)).toBeDefined();
  expect(screen.getByText("S-alfa")).toBeDefined();
});

test("il filtro per stato restringe l'elenco", async () => {
  finto(DATI);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  fireEvent.click(screen.getByRole("button", { name: /^scartato\s*1$/ }));
  expect(screen.queryByText("S-alfa")).toBeNull();
  expect(screen.getByText("S-beta")).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: /^tutti\s*3$/ }));
  expect(screen.getByText("S-alfa")).toBeDefined();
});

test("la ricerca guarda anche dove vive", async () => {
  finto(DATI);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  fireEvent.change(screen.getByLabelText("Cerca"), { target: { value: "gamma" } });
  expect(screen.queryByText("S-alfa")).toBeNull();
  expect(screen.getByText("S-beta")).toBeDefined();
});

test("copia il comando negli appunti", async () => {
  finto(DATI);
  const scrivi = vi.fn().mockResolvedValue();
  Object.defineProperty(navigator, "clipboard", { value: { writeText: scrivi }, configurable: true });
  render(<Esiti />);
  await screen.findByText("S-alfa");
  apri("S-alfa");
  fireEvent.click(screen.getByRole("button", { name: "Copia" }));
  expect(scrivi).toHaveBeenCalledWith("python -m alfa --x");
  expect(await screen.findByText("Copiato")).toBeDefined();
});

test("stato vuoto e errore sono detti a voce", async () => {
  finto([]);
  const { unmount } = render(<Esiti />);
  expect(await screen.findByText("Nessuno strumento adottato finora.")).toBeDefined();
  unmount();
  globalThis.fetch = vi.fn(() => Promise.resolve({
    ok: false, statusText: "boom", json: async () => ({}),
  }));
  render(<Esiti />);
  expect(await screen.findByText(/Non riesco a leggere gli esiti: boom/)).toBeDefined();
});

test("Aggiorna da GitHub mostra cambiati e problemi e aggiorna la lista", async () => {
  finto(DATI, { sync: {
    cambiati: [{ id: "alfa", campi: ["stato"] }], problemi: ["beta: gh fallito"],
    esiti: [rec("alfa", { strumento: "Alfa nuovo" })],
  } });
  render(<Esiti />);
  await screen.findByText("S-alfa");
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna da GitHub" }));
  await waitFor(() => expect(screen.getByText("Alfa nuovo")).toBeDefined());
  expect(screen.getByText("Aggiornati: alfa.")).toBeDefined();
  expect(screen.getByText("beta: gh fallito")).toBeDefined();
});

const SCHEDA = {
  a_cosa_serve: "Trascrive l'audio dei video.",
  problema: "Un reel parlato senza testo non dà tip.",
  funzionalita: ["trascrizione locale", "nessun costo a token"],
  passi: ["salva il link", "lancia ingest"],
  idea_originale: "Alternative self-hosted ai servizi a pagamento.",
  implementazione: "learn-core chiama video-understand.",
  nodi: ["Life", "ContentExtractor"],
  costo: "gratis",
};

test("raggruppa per categoria nell'ordine fisso, senza categoria in fondo", async () => {
  finto([
    rec("alfa", { categoria: "ingest" }),
    rec("beta", { categoria: "modelli" }),
    rec("gamma", { categoria: "boh" }),
    rec("delta", { categoria: "modelli", stato: "in_prova" }),
  ]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  const titoli = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
  expect(titoli).toEqual(["Modelli e gateway", "Ingestione contenuti", "Senza categoria"]);
  const modelli = screen.getByRole("region", { name: "Modelli e gateway" });
  expect(modelli.textContent).toContain("S-beta");
  expect(modelli.textContent).toContain("1 in uso");
  expect(modelli.textContent).toContain("1 in prova");
  expect(screen.getByRole("region", { name: "Senza categoria" }).textContent).toContain("S-gamma");
  expect(screen.getByRole("navigation", { name: "Vai alla categoria" }).textContent).toContain("Modelli e gateway · 2");
});

test("la riga dice a cosa serve; aperta, la scheda spiega e la storia racconta", async () => {
  finto([rec("alfa", { ...SCHEDA, categoria: "ingest", comando: "whisper x.mp3", guida: "## Guida\n\ntesto della guida", contenuto: contenuto() })]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  expect(screen.getByText("Trascrive l'audio dei video.")).toBeDefined();
  apri("S-alfa");
  expect(screen.getByText("Un reel parlato senza testo non dà tip.")).toBeDefined();
  expect(screen.getByText("nessun costo a token").tagName).toBe("LI");
  expect(screen.getByText("lancia ingest").closest("ol")).not.toBeNull();
  expect(screen.getByText("whisper x.mp3")).toBeDefined();
  expect(screen.getByText("Alternative self-hosted ai servizi a pagamento.")).toBeDefined();
  expect(screen.getByText("learn-core chiama video-understand.")).toBeDefined();
  expect(screen.getByLabelText("nodi che lo usano").textContent).toContain("ContentExtractor");
  expect(screen.getAllByText("gratis").length).toBeGreaterThan(0);
  // with a card, the long guide is folded until asked for
  expect(screen.queryByText("testo della guida")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /Guida completa/ }));
  expect(screen.getByText("testo della guida")).toBeDefined();
});

test("senza fonte la storia lo dice: idea interna", async () => {
  finto([rec("alfa", { ...SCHEDA, contenuto: [] })]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  apri("S-alfa");
  expect(screen.getByText("Idea interna, non da un contenuto esterno.")).toBeDefined();
});

test("gli stati hanno i nomi della dashboard", async () => {
  finto([rec("alfa"), rec("beta", { stato: "aperto" })]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  expect(screen.getByRole("button", { name: /^in uso\s*1$/ })).toBeDefined();
  expect(screen.getByRole("button", { name: /^da fare\s*1$/ })).toBeDefined();
});

test("la ricerca trova anche per nodo e per comando", async () => {
  finto([rec("alfa", { nodi: ["Marketing"] }), rec("beta", { comando: "codex2 login" })]);
  render(<Esiti />);
  await screen.findByText("S-alfa");
  fireEvent.change(screen.getByLabelText("Cerca"), { target: { value: "marketing" } });
  expect(screen.queryByText("S-beta")).toBeNull();
  fireEvent.change(screen.getByLabelText("Cerca"), { target: { value: "codex2" } });
  expect(screen.queryByText("S-alfa")).toBeNull();
  expect(screen.getByText("S-beta")).toBeDefined();
});
