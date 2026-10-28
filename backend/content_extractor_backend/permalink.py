"""L'indirizzo che apre QUEL post, e non un altro.

Il problema, misurato: aprendo `instagram.com/reel/<id>/` da un browser dove si
e' loggati, Instagram non mostra il post — apre il **lettore di reel**, che
scorre e porta altrove. Chi guardava la scheda finiva a leggere un contenuto
diverso da quello giudicato, e non c'era modo di accorgersene: l'indirizzo era
giusto, la pagina no.

La forma `/p/<id>/` apre il singolo post e non il lettore. Instagram stessa lo
dichiara: la pagina di `/reel/DbdQgnqTtFx/`, richiesta senza nessuna sessione,
porta `og:url = https://www.instagram.com/shwetacreates/p/DbdQgnqTtFx/`.

Qui si fa solo la parte che non costa una richiesta di rete e non puo'
sbagliare: riscrivere il segmento. L'autore, che solo `og:url` conosce, non
serve ad aprire il post — serve a leggerlo in un elenco, ed e' un di piu' che
non vale una chiamata di rete per contenuto.
"""
from __future__ import annotations

import re

_REEL = re.compile(
    r"^(?P<prima>https?://(?:www\.)?instagram\.com/)(?:reel|reels)/(?P<id>[^/?#]+)",
    re.IGNORECASE,
)


def canonico(url: str | None) -> str | None:
    """L'URL che apre esattamente questo post, o *url* se non c'e' niente da fare.

    Non inventa: tocca solo `instagram.com/reel/<id>` e lascia intatto tutto il
    resto — un link a un altro sito, un `/p/` gia' canonico, una stringa vuota.
    """
    if not url:
        return url
    trovato = _REEL.match(url.strip())
    if trovato is None:
        return url
    return f"{trovato.group('prima')}p/{trovato.group('id')}/"
