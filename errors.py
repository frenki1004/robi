"""Ecovacs error codes in plain Croatian, each with what to do about it.

Codes come from deebot_client.const.ERROR_CODES. "info" codes are messages
that don't need the user to fix anything; "error" codes do.
"""

from __future__ import annotations

from typing import Any

# code: (severity, title, steps)
_E = "error"
_I = "info"

ERRORS: dict[int, tuple[str, str, list[str]]] = {
    # --- robot ---------------------------------------------------------------
    101: (_E, "Baterija je skoro prazna", [
        "Vrati robota na stanicu dodirom na »Završi i vrati na stanicu«.",
        "Ako ne može sam, odnesi ga i stavi na stanicu.",
    ]),
    102: (_E, "Robot je podignut s poda", [
        "Spusti robota na ravan pod, sa svim kotačima na podu.",
        "Dodirni »Nastavi«.",
    ]),
    103: (_E, "Kotač je zapeo", [
        "Okreni robota i provjeri dva velika kotača.",
        "Izvadi kosu, konce ili ostatke koji su se zapleli.",
        "Provjeri da se kotači slobodno okreću, pa vrati robota na pod.",
    ]),
    104: (_E, "Senzori na dnu su prljavi", [
        "Okreni robota.",
        "Suhom mekanom krpom obriši male senzore uz rub donje strane.",
        "Vrati robota na pod i dodirni »Nastavi«.",
    ]),
    105: (_E, "Robot je zapeo", [
        "Pronađi robota i oslobodi ga (ispod namještaja, na kabelu, na rubu tepiha).",
        "Stavi ga na otvoren, ravan dio poda.",
        "Dodirni »Nastavi«.",
    ]),
    106: (_E, "Bočne četke su istrošene", [
        "Zamijeni bočne četke novima (odvrnu se ili samo izvuku).",
        "U aplikaciji ECOVACS resetiraj brojač četki.",
    ]),
    107: (_E, "Filter je istrošen", [
        "Izvadi spremnik za prašinu i iz njega filter.",
        "Stavi novi filter.",
        "U aplikaciji ECOVACS resetiraj brojač filtera.",
    ]),
    108: (_E, "Bočna četka je zapetljana", [
        "Okreni robota.",
        "S bočne četke odmotaj kosu i konce.",
        "Vrati robota na pod i dodirni »Nastavi«.",
    ]),
    109: (_E, "Glavna četka je zapetljana", [
        "Okreni robota naopako.",
        "Otvori poklopac glavne četke (pritisni kvačice) i izvadi četku.",
        "Odreži i izvuci kosu i konce s četke i s krajeva osovine.",
        "Vrati četku i poklopac, stavi robota na pod i dodirni »Nastavi«.",
    ]),
    110: (_E, "Spremnik za prašinu nije umetnut", [
        "Otvori gornji poklopac robota.",
        "Umetni spremnik za prašinu dok ne klikne.",
        "Dodirni »Nastavi«.",
    ]),
    111: (_E, "Branik je zapeo", [
        "Nekoliko puta lagano pritisni prednji branik da se oslobodi.",
        "Provjeri da ništa nije zaglavljeno ispod njega.",
        "Dodirni »Nastavi«.",
    ]),
    112: (_E, "Laserski senzor na vrhu ne radi", [
        "Provjeri da ništa ne pritišće okrugli senzor na vrhu robota.",
        "Pazi da robot nije zapeo ispod niskog namještaja.",
        "Ugasi i ponovno upali robota. Ako se ponavlja, javi servisu.",
    ]),
    113: (_E, "Glavna četka je istrošena", [
        "Zamijeni glavnu četku novom.",
        "U aplikaciji ECOVACS resetiraj brojač glavne četke.",
    ]),
    114: (_E, "Spremnik za prašinu je pun", [
        "Izvadi spremnik za prašinu i isprazni ga u smeće.",
        "Vrati ga dok ne klikne i dodirni »Nastavi«.",
    ]),
    115: (_E, "Problem s baterijom", [
        "Vrati robota na stanicu da se napuni.",
        "Ako se greška ponavlja, javi servisu.",
    ]),
    116: (_E, "Prednji senzor ne radi", [
        "Suhom krpom obriši prednji dio robota (senzore i kameru).",
        "Ugasi i ponovno upali robota.",
    ]),
    117: (_E, "Problem sa senzorom ravnoteže", [
        "Stavi robota na ravan pod i ostavi ga mirno minutu.",
        "Ugasi i ponovno upali robota.",
    ]),
    118: (_E, "Filter ili usis je začepljen", [
        "Izvadi spremnik za prašinu i očisti filter (istresi prašinu).",
        "Provjeri da ništa ne začepljuje otvor usisa ispod robota.",
    ]),
    119: (_E, "Problem s ventilatorom", [
        "Isprazni spremnik za prašinu i očisti filter.",
        "Ugasi i ponovno upali robota. Ako se ponavlja, javi servisu.",
    ]),
    120: (_E, "Problem sa spremnikom za vodu", [
        "Izvadi spremnik za vodu i ponovno ga umetni dok ne klikne.",
        "Provjeri ima li u njemu vode.",
    ]),
    121: (_E, "Nosač krpe je zapeo", [
        "Okreni robota i provjeri nosače krpi.",
        "Ukloni sve što se zaplelo, pa ponovno postavi krpe.",
    ]),
    125: (_E, "Problem sa spremnikom za vodu", [
        "Izvadi spremnik za vodu i ponovno ga umetni.",
        "Ako se ponavlja, javi servisu.",
    ]),
    126: (_E, "Spremnik za vodu nije umetnut", [
        "Umetni spremnik za vodu dok ne klikne.",
        "Dodirni »Nastavi«.",
    ]),
    128: (_E, "Krpe za brisanje nisu obje postavljene", [
        "Okreni robota.",
        "Postavi obje krpe na nosače dok ne sjednu.",
        "Dodirni »Nastavi«.",
    ]),
    129: (_E, "Krpa za brisanje je zapetljana", [
        "Okreni robota.",
        "Skini krpe i ukloni kosu ili konce s krpi i nosača.",
        "Vrati krpe i dodirni »Nastavi«.",
    ]),
    201: (_E, "Filter zraka nije umetnut", [
        "Umetni filter u spremnik za prašinu.",
    ]),
    202: (_E, "Ultrazvučni senzor (za tepih) ne radi", [
        "Obriši senzor na donjoj strani robota suhom krpom.",
    ]),
    203: (_E, "Mali prednji kotač je zapeo", [
        "Okreni robota i očisti mali okretni kotačić sprijeda.",
        "Izvuci kosu oko osovine kotačića.",
    ]),
    204: (_E, "Kotač visi u zraku", [
        "Robot je vjerojatno zapeo na pragu ili rubu.",
        "Stavi ga na ravan pod i dodirni »Nastavi«.",
    ]),
    205: (_E, "Modul za sterilizaciju je istrošen", [
        "Zamijeni modul za sterilizaciju vode.",
    ]),
    206: (_E, "Problem s modulom za sterilizaciju", [
        "Izvadi i ponovno umetni modul za sterilizaciju.",
    ]),
    207: (_E, "Kvar modula za sterilizaciju", [
        "Izvadi modul za sterilizaciju. Ako se ponavlja, javi servisu.",
    ]),
    209: (_E, "Senzor udaljenosti ne radi", [
        "Suhom krpom obriši senzore na prednjem dijelu robota.",
        "Ugasi i ponovno upali robota.",
    ]),
    601: (_E, "Bočna četka je zapetljana", [
        "Okreni robota i odmotaj kosu i konce s bočne četke.",
    ]),
    602: (_E, "Glavna četka je zapetljana", [
        "Okreni robota, izvadi glavnu četku i očisti kosu i konce.",
        "Vrati četku i dodirni »Nastavi«.",
    ]),
    1007: (_E, "Krpa za brisanje je začepljena", [
        "Skini krpe, isperi ih i vrati na robota.",
    ]),
    1027: (_E, "Robot ne može pronaći stanicu", [
        "Robot se vraća na mjesto gdje je počeo.",
        "Odnesi ga i stavi na stanicu ručno.",
        "Provjeri da je stanica uključena u struju i da ništa ne stoji ispred nje.",
    ]),
    1052: (_E, "Vrijeme je za zamjenu krpi", [
        "Zamijeni krpe za brisanje novima.",
    ]),
    1062: (_E, "Robot se izgubio na karti", [
        "Robot počinje novu kartu. Vrati ga na stanicu.",
        "Ne pomiči stanicu, inače karta ne valja.",
    ]),
    1068: (_E, "Robot se izgubio i vraća na stanicu", [
        "Pričekaj da se vrati. Ako ne uspije, odnesi ga na stanicu.",
    ]),
    1088: (_E, "Robot se izgubio na karti", [
        "Odnesi robota na stanicu i pokreni čišćenje ponovno.",
    ]),
    2036: (_E, "Prepreka na putu", [
        "Ukloni predmet ispred robota (cipele, kabeli, igračke).",
        "Dodirni »Nastavi«.",
    ]),
    4200: (_E, "Robot nije dostupan", [
        "Provjeri je li robot uključen.",
        "Provjeri radi li Wi-Fi u kući.",
    ]),
    # --- station -------------------------------------------------------------
    301: (_E, "Spremnik čiste vode je prazan", [
        "Izvadi spremnik čiste vode iz stanice (lijevi).",
        "Napuni ga vodom iz slavine do oznake MAX i vrati ga.",
    ]),
    302: (_E, "Spremnik prljave vode je pun", [
        "Izvadi spremnik prljave vode iz stanice (desni).",
        "Isprazni ga u WC ili sudoper, isperi i vrati.",
    ]),
    303: (_E, "Spremnik čiste vode nije umetnut", [
        "Umetni spremnik čiste vode u stanicu dok ne sjedne.",
    ]),
    304: (_E, "Spremnik prljave vode nije umetnut", [
        "Umetni spremnik prljave vode u stanicu dok ne sjedne.",
    ]),
    305: (_E, "Spremnik prljave vode je pun", [
        "Isprazni spremnik prljave vode iz stanice, isperi ga i vrati.",
    ]),
    306: (_E, "Filter u stanici nije umetnut", [
        "Umetni filter u posudu za pranje krpi na dnu stanice.",
    ]),
    307: (_E, "Problem sa stanicom", [
        "Iskopčaj stanicu iz struje na 10 sekundi pa je ponovno ukopčaj.",
        "Ako se ponavlja, javi servisu.",
    ]),
    308: (_E, "Robot i stanica se ne čuju", [
        "Provjeri je li stanica uključena u struju.",
        "Stavi robota ravno na stanicu.",
    ]),
    310: (_E, "Poklopac stanice je otvoren", [
        "Zatvori gornji poklopac stanice dok ne klikne.",
    ]),
    311: (_E, "Zamijeni vrećicu za prašinu", [
        "Otvori poklopac stanice, izvadi vrećicu i stavi novu.",
    ]),
    312: (_E, "Vrećica za prašinu je puna", [
        "Otvori poklopac stanice, izvadi punu vrećicu i stavi novu.",
    ]),
    314: (_I, "Modul za vodu nije umetnut", []),
    315: (_I, "Modul za dovod vode nije umetnut", []),
    316: (_E, "Posuda za prljavštinu u stanici je puna", [
        "Izvadi posudu za pranje krpi na dnu stanice i očisti je.",
    ]),
    317: (_E, "Spremnik čiste vode se ne puni", [
        "Napuni spremnik čiste vode ručno i vrati ga u stanicu.",
    ]),
    318: (_E, "Spremnik prljave vode je pun", [
        "Isprazni spremnik prljave vode iz stanice, isperi ga i vrati.",
    ]),
    319: (_I, "Sredstvo za čišćenje je pri kraju", [
        "Dolij sredstvo za čišćenje u stanicu kad stigneš.",
    ]),
    322: (_E, "Spremnik čiste vode je prazan ili nije umetnut", [
        "Napuni spremnik čiste vode i umetni ga u stanicu dok ne sjedne.",
    ]),
    323: (_E, "Spremnik prljave vode je pun ili nije umetnut", [
        "Isprazni spremnik prljave vode, isperi ga i umetni u stanicu.",
    ]),
    # --- messages that need no action ----------------------------------------
    1021: (_I, "Čišćenje je završeno", []),
    1024: (_I, "Baterija je slaba, robot se vraća puniti", []),
    1053: (_I, "Zadatak prekinut, robot se vraća puniti", []),
    1061: (_I, "Robot se snašao i nastavlja čistiti", []),
    1071: (_I, "Robot je ažurirao svoj položaj", []),
    1094: (_I, "Krpe se suše", []),
}

NO_ERROR = {0, 100}


def describe(code: int, fallback: str | None = None) -> dict[str, Any] | None:
    """Return {code, severity, title, steps} for an error code, or None if fine."""
    if code in NO_ERROR:
        return None
    if code in ERRORS:
        severity, title, steps = ERRORS[code]
    else:
        severity, title = _E, f"Robot javlja grešku {code}"
        steps = ["Pogledaj robota i aplikaciju ECOVACS za više detalja."]
        if fallback:
            steps.insert(0, f"Opis (engleski): {fallback}")
    return {"code": code, "severity": severity, "title": title, "steps": steps}
