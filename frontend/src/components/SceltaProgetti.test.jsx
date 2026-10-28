import { render, screen, fireEvent } from "@testing-library/react";
import SceltaProgetti from "./SceltaProgetti";

vi.mock("../hooks/useRepos", () => ({
  useRepos: () => ({
    errore: null,
    elenco: [
      { nome: "Offerte", slug: "o/Offerte", esiste: true },
      { nome: "Marketing", slug: "o/Marketing", esiste: false, motivo: "il repo o/Marketing non esiste su GitHub" },
    ],
  }),
}));

test("un repo che esiste si sceglie", () => {
  const onCambia = vi.fn();
  render(<SceltaProgetti scelti={[]} onCambia={onCambia} />);
  fireEvent.click(screen.getByRole("button", { name: "+ Offerte" }));
  expect(onCambia).toHaveBeenCalledWith(["Offerte"]);
});

test("un repo che su GitHub non esiste è disabilitato e lo dice", () => {
  const onCambia = vi.fn();
  render(<SceltaProgetti scelti={[]} onCambia={onCambia} />);
  const spento = screen.getByRole("button", { name: /Marketing/ });
  expect(spento.disabled).toBe(true);
  expect(spento.textContent).toContain("non esiste su GitHub");
  fireEvent.click(spento);
  expect(onCambia).not.toHaveBeenCalled();
});
