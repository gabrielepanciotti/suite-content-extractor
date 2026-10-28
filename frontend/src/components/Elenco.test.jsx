import { render, screen, fireEvent } from "@testing-library/react";
import Elenco from "./Elenco";

const riga = (id, over = {}) => ({
  source_id: id, titolo: `T-${id}`, stato: "da_vedere",
  stato_etichetta: "da vedere", quante_tip: 2, caricato: "2026-10-01",
  manca_allegato: false, in_rielaborazione: false, ...over,
});

const rendi = (schede, props = {}) => {
  const onApri = vi.fn();
  render(
    <Elenco schede={schede} correnteId="a" onApri={onApri}
            solo="tutti" onSolo={() => {}} {...props} />,
  );
  return onApri;
};

test("segnala i post a cui manca contenuto e quelli in rielaborazione", () => {
  rendi([riga("a", { manca_allegato: true }), riga("b", { in_rielaborazione: true })]);
  expect(screen.getByText("manca contenuto")).toBeDefined();
  expect(screen.getByText("rielaborazione…")).toBeDefined();
});

test("le frecce scorrono da un contenuto all'altro", () => {
  const onApri = rendi([riga("a"), riga("b"), riga("c")]);
  fireEvent.click(screen.getByRole("button", { name: /successivo/i }));
  expect(onApri).toHaveBeenCalledWith("b");
  expect(screen.getByRole("button", { name: /precedente/i }).disabled).toBe(true);
});

test("cliccare una riga apre quel contenuto", () => {
  const onApri = rendi([riga("a"), riga("b")]);
  fireEvent.click(screen.getByText("T-b"));
  expect(onApri).toHaveBeenCalledWith("b");
});

test("a materiale consegnato non resta l'etichetta che dice che manca", () => {
  rendi([riga("a", { materiale_aggiunto: true })]);
  expect(screen.getByText("materiale aggiunto")).toBeDefined();
  expect(screen.queryByText("manca contenuto")).toBeNull();
});

test("ordina per efficacia stimata, e per data se lo chiedi", () => {
  const schede = [
    riga("a", { impatto: 2, caricato: "2026-10-03" }),
    riga("b", { impatto: 5, caricato: "2026-10-01" }),
    riga("c", { impatto: null, caricato: "2026-10-09" }),
  ];
  const nomi = () => screen.getAllByRole("button")
    .map((b) => b.textContent).filter((t) => t.startsWith("T-")).map((t) => t[2]);
  const { unmount } = render(
    <Elenco schede={schede} correnteId="a" onApri={() => {}} solo="tutti"
            onSolo={() => {}} ordine="efficacia" />,
  );
  expect(nomi()).toEqual(["b", "a", "c"]);
  unmount();
  render(
    <Elenco schede={schede} correnteId="a" onApri={() => {}} solo="tutti"
            onSolo={() => {}} ordine="recenti" />,
  );
  expect(nomi()).toEqual(["c", "a", "b"]);
});
