/** What a record's `stato` means to a person, in display order. */
export const STATI = ["portato", "in_prova", "aperto", "unito", "scartato"];

export const ETICHETTA_STATO = {
  portato: "in uso",
  in_prova: "in prova",
  aperto: "da fare",
  unito: "unito",
  scartato: "scartato",
};

/** Badge tone of the design system for each state. */
export const TONO_STATO = {
  portato: "success",
  in_prova: "warning",
  aperto: "info",
  unito: undefined,
  scartato: "danger",
};

/** Colour of the small dot in a row (design-system tokens). */
export const PUNTO_STATO = {
  portato: "bg-success",
  in_prova: "bg-warning",
  aperto: "bg-info",
  unito: "bg-muted",
  scartato: "bg-danger",
};

/** `https://github.com/o/r/issues/69` -> `r#69`; anything else stays as is. */
export const etichettaIssue = (url) => {
  const m = /github\.com\/[^/]+\/([^/]+)\/(?:issues|pull)\/(\d+)/.exec(
    url || "",
  );
  return m ? `${m[1]}#${m[2]}` : url;
};
