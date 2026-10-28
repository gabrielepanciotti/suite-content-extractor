import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import SceltaIstanza, { BadgeIstanza } from "./SceltaIstanza";

const ISTANZE = [
  { id: "alfa", status: "ok", reason: null, default: true },
  { id: "beta", status: "unreachable", reason: "path assente: /x", default: false },
];

describe("SceltaIstanza", () => {
  it("offers «Tutte» plus every instance, the unreachable one named", () => {
    render(<SceltaIstanza istanze={ISTANZE} scelta="" onScegli={() => {}} />);
    expect(screen.getByRole("button", { name: "Tutte" }).getAttribute("aria-pressed")).toBe("true");
    const beta = screen.getByRole("button", { name: /beta/ });
    expect(beta.getAttribute("title")).toBe("Irraggiungibile: path assente: /x");
  });

  it("chooses an instance", () => {
    const onScegli = vi.fn();
    render(<SceltaIstanza istanze={ISTANZE} scelta="" onScegli={onScegli} />);
    fireEvent.click(screen.getByRole("button", { name: "alfa" }));
    expect(onScegli).toHaveBeenCalledWith("alfa");
  });

  it("badge shows the id, and nothing without one", () => {
    const { container, rerender } = render(<BadgeIstanza id="alfa" />);
    expect(container.textContent).toBe("alfa");
    rerender(<BadgeIstanza id={null} />);
    expect(container.innerHTML).toBe("");
  });
});
