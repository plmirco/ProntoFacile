# ods_reader.py
import pandas as pd
from config_rules import OPERATORI_ESCLUSI_SEMPRE

_CACHE_ODS = {}

# Elenco completo delle causali di assenza nel foglio
MOTIVI_ASSENZA_TASSATIVA = [
    "MALATTIA", "MAL", "FERIE", "FER", "P.FERIE", "PERMESSO", "PERM", 
    "RECUPERO", "REC.C", "REC. C", "REC", "ASPETTATIVA", "CONGEDO", "CONG", 
    "LEGGE 104", "104", "INFORTUNIO", "RIPOSO", "RIP"
]

OPERATORI_SINGOLI_SPECIALI = [
    "PALMIERI", "CALÒ", "CALO", "FLORIDIA", "MINGHETTI", "TREVISANI"
]

def inizializza_cache_ods(percorso_ods):
    global _CACHE_ODS
    _CACHE_ODS.clear()
    _CACHE_ODS = pd.read_excel(percorso_ods, sheet_name=None, engine='odf')

def pulisci_stringa(valore):
    if pd.isna(valore):
        return ""
    return str(valore).strip().upper()

def carica_anagrafica_turni(percorso_ods):
    global _CACHE_ODS
    if not _CACHE_ODS:
        inizializza_cache_ods(percorso_ods)

    nome_foglio_dati = next((s for s in _CACHE_ODS.keys() if pulisci_stringa(s).lower() == 'dati'), None)
    if not nome_foglio_dati:
        return [], []

    df_dati = _CACHE_ODS[nome_foglio_dati]
    matrice = df_dati.to_numpy()
    
    turno_a, turno_b = [], []
    num_righe, num_colonne = matrice.shape

    for riga in range(num_righe):
        for col in range(num_colonne):
            cel_str = pulisci_stringa(matrice[riga, col])

            if not cel_str or cel_str == "NAN" or "TURNO" in cel_str or "NOME" in cel_str:
                continue

            if any(escluso in cel_str for escluso in OPERATORI_ESCLUSI_SEMPRE):
                continue

            gruppo = None
            for offset in [1, -1, 2, -2]:
                c_adj = col + offset
                if 0 <= c_adj < num_colonne:
                    str_g = pulisci_stringa(matrice[riga, c_adj])
                    if str_g in ["A", "B"]:
                        gruppo = str_g
                        break

            if gruppo is not None:
                # Cerca di estrarre la parola del cognome principale
                parti = cel_str.split()
                cognome = parti[0] if len(parti) > 0 else cel_str

                if gruppo == "A":
                    if cognome not in turno_a:
                        turno_a.append(cognome)
                    if "FANTAZZINI" in cel_str and "FANTAZZINI" not in turno_a:
                        turno_a.append("FANTAZZINI")
                elif gruppo == "B":
                    if cognome not in turno_b:
                        turno_b.append(cognome)
                    if "FANTAZZINI" in cel_str and "FANTAZZINI" not in turno_b:
                        turno_b.append("FANTAZZINI")

    return turno_a, turno_b

def estrai_dati_giorno(percorso_ods, nome_foglio_giorno):
    global _CACHE_ODS
    if not _CACHE_ODS:
        inizializza_cache_ods(percorso_ods)

    turno_a, turno_b = carica_anagrafica_turni(percorso_ods)

    target_str = pulisci_stringa(nome_foglio_giorno)
    foglio_target = next((s for s in _CACHE_ODS.keys() if pulisci_stringa(s) == target_str), None)
    
    if not foglio_target:
        return [], [], [], [], []

    df_giorno = _CACHE_ODS[foglio_target]
    matrice_giorno = df_giorno.to_numpy()

    indicatore_b2 = ""
    if matrice_giorno.shape[0] > 0 and matrice_giorno.shape[1] > 1:
        indicatore_b2 = pulisci_stringa(matrice_giorno[0, 1])

    if "TURNO B" in indicatore_b2 or "TURNO:B" in indicatore_b2 or indicatore_b2 == "B":
        squadra_mattina = list(turno_b)
        squadra_pomeriggio = list(turno_a)
    else:
        squadra_mattina = list(turno_a)
        squadra_pomeriggio = list(turno_b)

    assenti = set()
    tutti_ops = set(turno_a + turno_b)

    num_righe, num_colonne = matrice_giorno.shape
    for r in range(num_righe):
        for c in range(num_colonne):
            cel_upper = pulisci_stringa(matrice_giorno[r, c])
            if cel_upper and cel_upper != "NAN":
                # Se la cella contiene un motivo di assenza
                if any(motivo in cel_upper for motivo in MOTIVI_ASSENZA_TASSATIVA):
                    for op in tutti_ops:
                        if op in cel_upper:
                            assenti.add(op)

    speciali_mattina = [op for op in squadra_mattina if op in OPERATORI_SINGOLI_SPECIALI and op not in assenti]
    speciali_pomeriggio = [op for op in squadra_pomeriggio if op in OPERATORI_SINGOLI_SPECIALI and op not in assenti]

    disp_mattina = [op for op in squadra_mattina if op not in assenti and op not in OPERATORI_ESCLUSI_SEMPRE and op not in OPERATORI_SINGOLI_SPECIALI]
    disp_pomeriggio = [op for op in squadra_pomeriggio if op not in assenti and op not in OPERATORI_ESCLUSI_SEMPRE and op not in OPERATORI_SINGOLI_SPECIALI]

    return disp_mattina, disp_pomeriggio, speciali_mattina, speciali_pomeriggio, sorted(list(assenti))
