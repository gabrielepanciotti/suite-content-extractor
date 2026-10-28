/** Un href che arriva dal contenuto (o da un'issue aperta da `gh`) non è
 *  testo qualunque: finisce dentro un `href` reso a chi apre la scheda senza
 *  autenticarsi sulla tailnet. Solo http/https passano; il resto (in primis
 *  `javascript:`) torna null e il chiamante non rende il link. */
const SCHEMI_AMMESSI = new Set(["http:", "https:"]);

export const hrefSicuro = (url) => {
  if (!url) return null;
  try {
    const analizzato = new URL(url, window.location.href);
    return SCHEMI_AMMESSI.has(analizzato.protocol) ? url : null;
  } catch {
    return null;
  }
};

/** `instagram:ID` -> link to the post; other sources have no link. */
export const fonteLink = (fonte) => {
  const m = /^instagram:(.+)$/.exec(fonte || "");
  return m ? `https://www.instagram.com/p/${m[1]}/` : null;
};
