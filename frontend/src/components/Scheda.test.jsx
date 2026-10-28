import { render, screen, fireEvent, waitFor } from "@testing-library/react";

beforeEach(() => {
  window.localStorage.clear();
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve([
          { nome: "Life", slug: "o/Life" },
          { nome: "Offerte", slug: "o/Offerte" },
          { nome: "Cruscotto", slug: "o/Cruscotto" },
        ]),
    }),
  );
});
import Scheda from "./Scheda";

const tip = (over = {}) => ({
  id: "aaa", titolo: "Usa Scrapling", corpo: "corpo", stato: "pending",
  pros: ["è documentato"], cons: ["raddoppia i token"],
  raccomandazione: "adopt", approfondimento: null,
  degradato: "no media for reel", nota_giudizio: null,
  motivo_verdetto: "fuori obiettivo",
  repo: "Life (packages/learn-core, non verificato)", repo_suggerito: "Life",
  motivo_fallimento: null, tipo: "strumento", strumento: "Scrapling",
  ...over,
});

const USO = tip({
  id: "bbb", titolo: "Collegalo all'agente", tipo: "utilizzo",
  degradato: null, motivo_verdetto: null,
});

const scheda = (over = {}) => {
  const base = {
    source_id: "instagram:ABC", titolo: "Scrapling", url: "https://x/",
    origine: "telegram", caricato: "2026-09-01T00:00:00+00:00",
    data_approssimata: false, stato: "da_vedere", stato_etichetta: "da vedere",
    quante_tip: 2, esito: "2 tip",
    gruppi: [{ strumento: "Scrapling", tip: tip(), utilizzi: [USO] }],
    pratiche: [],
    ...over,
  };
  // La lista piatta e' una vista delle altre due: tenerle a mano nei test
  // le farebbe divergere proprio dove il gate le conta.
  base.tip = base.gruppi.flatMap((g) => [g.tip, ...g.utilizzi].filter(Boolean))
    .concat(base.pratiche);
  return base;
};

const rendi = (over = {}, props = {}) =>
  render(
    <Scheda
      scheda={scheda(over)}
      onDecidiTip={props.onDecidiTip || (() => {})}
      onDecidiStrumento={props.onDecidiStrumento || (() => {})}
      onProssimo={props.onProssimo}
      onDecidiPacchetto={props.onDecidiPacchetto}
    />,
  );

test("mostra pro e contro, non solo la raccomandazione", () => {
  rendi();
  expect(screen.getAllByText("è documentato").length).toBeGreaterThan(0);
  expect(screen.getAllByText("raddoppia i token").length).toBeGreaterThan(0);
});

test("il degrado si vede accanto alla raccomandazione, non in fondo", () => {
  rendi();
  expect(screen.getByText(/no media/i)).toBeDefined();
});

test("dice perché il giudizio è quello, accanto al verdetto", () => {
  rendi();
  expect(screen.getByText("fuori obiettivo")).toBeDefined();
});

test("lo strumento sta sopra, i suoi utilizzi sotto", () => {
  rendi();
  expect(screen.getByText(/dove e come si può integrare/i)).toBeDefined();
  expect(screen.getByText("Collegalo all'agente")).toBeDefined();
});

test("approvare uno strumento avvisa che vale anche per i suoi utilizzi", () => {
  rendi();
  expect(screen.getByText(/vale anche per tutti i suoi utilizzi/i)).toBeDefined();
});

test("decide anche senza motivo: vale quello del giudizio", () => {
  const onDecidiStrumento = vi.fn();
  rendi({}, { onDecidiStrumento });
  fireEvent.click(screen.getAllByRole("button", { name: /^approva$/i })[0]);
  fireEvent.click(screen.getByRole("button", { name: /conferma/i }));
  expect(onDecidiStrumento).toHaveBeenCalledWith("aaa", expect.objectContaining({
    verdict: "adopted", reason: "",
  }));
});

test("approvare lo strumento passa nota e progetti", async () => {
  const onDecidiStrumento = vi.fn();
  rendi({}, { onDecidiStrumento });
  fireEvent.click(screen.getAllByRole("button", { name: /^approva$/i })[0]);
  fireEvent.change(screen.getByLabelText(/motivo/i), { target: { value: "serve" } });
  fireEvent.change(screen.getByLabelText(/come implementarlo/i), {
    target: { value: "parti da fetch_page" },
  });
  // Nessun repo e' preselezionato dal giudizio: si sceglie dall'elenco.
  fireEvent.click(await screen.findByRole("button", { name: "+ Offerte" }));
  fireEvent.click(screen.getByRole("button", { name: /conferma/i }));
  expect(onDecidiStrumento).toHaveBeenCalledWith("aaa", {
    verdict: "adopted",
    reason: "serve",
    nota: "parti da fetch_page",
    repos: ["Offerte"],
    entita: null,
  });
});

test("declinando non si chiede come implementarlo", () => {
  rendi();
  fireEvent.click(screen.getAllByRole("button", { name: /^declina$/i })[0]);
  expect(screen.queryByLabelText(/come implementarlo/i)).toBeNull();
});

test("un utilizzo si decide da solo, senza cascata", () => {
  const onDecidiTip = vi.fn();
  rendi({}, { onDecidiTip });
  // Il secondo modulo di decisione della pagina e' quello dell'utilizzo.
  fireEvent.click(screen.getAllByRole("button", { name: /^approva$/i })[1]);
  fireEvent.change(screen.getByLabelText(/motivo/i), { target: { value: "ok" } });
  fireEvent.click(screen.getByRole("button", { name: /conferma/i }));
  expect(onDecidiTip).toHaveBeenCalledWith("bbb", expect.objectContaining({
    verdict: "adopted", reason: "ok",
  }));
});

test("non si passa al prossimo finché resta qualcosa di indeciso", () => {
  rendi({}, { onProssimo: () => {} });
  expect(screen.getByText(/restano 2 da decidere/i)).toBeDefined();
  expect(screen.getByRole("button", { name: /prossimo contenuto/i }).disabled).toBe(true);
});

test("deciso tutto, il prossimo si apre", () => {
  rendi(
    {
      gruppi: [{
        strumento: "Scrapling",
        tip: tip({ stato: "adopted" }),
        utilizzi: [{ ...USO, stato: "adopted" }],
      }],
    },
    { onProssimo: () => {} },
  );
  // In cima e in fondo: due bottoni, entrambi attivi.
  const bottoni = screen.getAllByRole("button", { name: /prossimo contenuto/i });
  expect(bottoni).toHaveLength(2);
  expect(bottoni.every((b) => !b.disabled)).toBe(true);
});

test("una frase del giudizio non diventa mai un progetto", async () => {
  rendi({
    gruppi: [],
    pratiche: [tip({ id: "ddd", tipo: "pratica", strumento: null,
                     repo: "boh, una frase", repo_suggerito: null })],
  });
  fireEvent.click(screen.getByRole("button", { name: /^approva$/i }));
  await waitFor(() => expect(screen.getByRole("button", { name: "+ Life" })).toBeDefined());
  expect(screen.queryByRole("button", { name: /togli/i })).toBeNull();
  expect(screen.getByText(/nessuna issue/i)).toBeDefined();
});

test("una pratica non finisce sotto nessuno strumento", () => {
  rendi({
    gruppi: [],
    pratiche: [tip({ id: "ccc", titolo: "Una pratica", tipo: "pratica", strumento: null })],
  });
  expect(screen.queryByText(/dove e come si può integrare/i)).toBeNull();
  expect(screen.getByText("Una pratica")).toBeDefined();
});

test("il post che promette un file chiede l'azione, col link canonico", () => {
  rendi({
    url: "https://www.instagram.com/reel/ABC/",
    url_canonico: "https://www.instagram.com/p/ABC/",
    manca_allegato: true,
  });
  expect(screen.getByText("manca link/documento")).toBeDefined();
  expect(screen.getByRole("link", { name: "Apri il post" }).getAttribute("href"))
    .toBe("https://www.instagram.com/p/ABC/");
});

test("un carosello non chiede niente all'utente: dice che manca a noi", () => {
  rendi({ da_leggere_immagini: true });
  expect(screen.getByText("da leggere nelle immagini")).toBeDefined();
  // Nessuna azione da fare: il bottone dell'altro avviso non deve comparire.
  expect(screen.queryByText("Apri il post")).toBeNull();
});

test("su un contenuto riuscito non compare nessuno dei due avvisi", () => {
  rendi();
  expect(screen.queryByText("manca link/documento")).toBeNull();
  expect(screen.queryByText("da leggere nelle immagini")).toBeNull();
});

test("la tip fallita dice perché non è stata estratta", () => {
  rendi({
    gruppi: [],
    pratiche: [
      tip({
        id: "ccc", stato: "failed", corpo: "", tipo: "pratica",
        strumento: null, motivo_fallimento: "rimanda al video",
      }),
    ],
  });
  expect(screen.getByText(/rimanda al video/)).toBeDefined();
});

test("sul post che promette un file si può caricare quello che si è ricevuto", async () => {
  const onMateriale = vi.fn().mockResolvedValue({ stato: "in_corso" });
  render(
    <Scheda
      scheda={scheda({ manca_allegato: true, url_canonico: "https://i/p/A/" })}
      onDecidiTip={() => {}}
      onDecidiStrumento={() => {}}
      onMateriale={onMateriale}
    />,
  );
  fireEvent.change(screen.getByLabelText(/link che hai ricevuto/i), {
    target: { value: "https://drive/x.pdf" },
  });
  fireEvent.click(screen.getByText("Aggiungi e rielabora"));
  await waitFor(() =>
    expect(onMateriale).toHaveBeenCalledWith({
      link: "https://drive/x.pdf",
      file: null,
    }),
  );
});

test("senza niente da mandare il bottone resta spento", () => {
  render(
    <Scheda
      scheda={scheda({ manca_allegato: true })}
      onDecidiTip={() => {}}
      onDecidiStrumento={() => {}}
      onMateriale={() => {}}
    />,
  );
  expect(screen.getByText("Aggiungi e rielabora").closest("button").disabled)
    .toBe(true);
});

test("quando il materiale è arrivato l'etichetta non lo chiede più", () => {
  render(
    <Scheda
      scheda={scheda({ manca_allegato: true })}
      onDecidiTip={() => {}}
      onDecidiStrumento={() => {}}
      onMateriale={() => {}}
      lavoro={{ stato: "finita", esito: "3 tip sulla scheda" }}
    />,
  );
  expect(screen.getByText("materiale aggiunto")).toBeDefined();
  expect(screen.queryByText("manca link/documento")).toBeNull();
});


test("una nota scritta a meta' sopravvive a un ricaricamento della pagina", async () => {
  const { unmount } = rendi({ gruppi: [], pratiche: [tip({ id: "ppp", tipo: "pratica", strumento: null })] });
  fireEvent.click(screen.getByRole("button", { name: /^approva$/i }));
  fireEvent.change(screen.getByLabelText("come implementarlo"), {
    target: { value: "nota a meta'" },
  });
  unmount();
  rendi({ gruppi: [], pratiche: [tip({ id: "ppp", tipo: "pratica", strumento: null })] });
  expect(screen.getByLabelText("come implementarlo").value).toBe("nota a meta'");
});

test("nel modulo prima si sceglie l'entità, poi (facoltativo) il progetto", async () => {
  const onDecidiStrumento = vi.fn();
  rendi({}, { onDecidiStrumento });
  fireEvent.click(screen.getAllByRole("button", { name: /^approva$/i })[0]);
  expect(screen.getByText(/dove lo mettiamo/i)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Life personal" }));
  fireEvent.click(screen.getByRole("button", { name: /conferma/i }));
  expect(onDecidiStrumento.mock.calls[0][1]).toMatchObject({
    entita: "Life personal",
    repos: [],
  });
});

test("con piu' strumenti aperti si possono decidere tutti insieme", () => {
  const due = [
    { strumento: "A", tip: tip({ id: "a1", strumento: "A" }), utilizzi: [] },
    { strumento: "B", tip: tip({ id: "b1", strumento: "B" }), utilizzi: [] },
  ];
  render(
    <Scheda
      scheda={scheda({ gruppi: due })}
      onDecidiTip={() => {}}
      onDecidiStrumento={() => {}}
      onDecidiTutti={() => {}}
      onDecidiPacchetto={() => {}}
    />,
  );
  expect(screen.getByText(/un'issue per ognuno dei 2 strumenti/i)).toBeDefined();
});

test("anche con uno strumento si puo' decidere tutto il contenuto in una volta", () => {
  rendi({}, { onDecidiPacchetto: () => {} });
  expect(screen.getByText(/decidi tutto insieme: 2 tip/i)).toBeDefined();
});
