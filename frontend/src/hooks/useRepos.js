import { useEffect, useState } from "react";
import { repos as leggiRepos } from "../lib/api";

let cache = null;

/** The projects an issue can be opened in, read once per page load.
 *  Every decision form asks the same question; asking the server once per
 *  card would be one request per tip for an answer that does not change. */
export function useRepos() {
  const [elenco, setElenco] = useState(cache ?? []);
  const [errore, setErrore] = useState(null);
  useEffect(() => {
    if (cache) return;
    leggiRepos()
      .then((r) => {
        cache = r;
        setElenco(r);
      })
      .catch((e) => setErrore(e.message || "errore sconosciuto"));
  }, []);
  return { elenco, errore };
}
