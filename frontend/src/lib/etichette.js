// Values the backend stores as identifiers, shown to a person in Italian.
export const ORIGINE = {
  "instagram-export": "salvati di Instagram",
  telegram: "Telegram",
  cli: "a mano",
};

export const origine = (valore) => ORIGINE[valore] ?? valore;
