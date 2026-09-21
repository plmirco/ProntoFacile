# ods_reader.py
import pandas as pd
import numpy as np
from config_rules import OPERATORI_ESCLUSI_SEMPRE

_CACHE_ODS = {}
MOTIVI_ASSENZA_REALE = ["FERIE", "MALATTIA", "MAL", "PERMESSO", "POLIGONO", "CORSO", "CORSI", "RECUPERO", "REC.C", "REC. C"]

def inizializza_cache_ods(percorso_ods):
    global _CACHE_ODS
    _CACHE_ODS.clear()
    _CACHE_ODS = pd.read_excel(percorso_ods, sheet_name=None, engine='odf')

def carica_anagrafica_turni(percorso_ods):
    global _CACHE_ODS
    if not _CACHE_ODS:
        inizializza_cache_ods(percorso_ods)

    nome_foglio_dati = next((s for s in _CACHE_ODS.keys() if str(s).strip().lower() == 'dati'), None)
    if not nome_foglio_dati:
        return [], []

    # Conversione del foglio Dati in Matrice NumPy pura (niente Serie Pandas)
    df_dati = _CACHE_ODS[nome_foglio_dati]
    matrice = df_dati.astype(str).to_numpy()
    
    turno_a, turno_b = [], []
    num_righe, num_colonne = matrice.shape

    for riga in range(num_righe):
        for col in range(num_colonne):
            cel_str = matrice[riga, col].strip().upper()

            if not cel_str or cel_str == "NAN" or "TURNO" in cel_str or "NOME" in cel_str:
                continue

            # Verifica esclusi
            if any(escluso in cel_str for escluso in OPERATORI_ESCLUSI_SEMPRE):
                continue

            # Cerca il Gruppo (A o B) nelle celle adiacenti
            gruppo = None
            for offset in [1, -1, 2, -2]:
                c_adj = col + offset
                if 0 <= c_adj < num_colonne:
                    str_g = matrice[riga, c_adj].strip().upper()
                    if str_g in ["A", "B"]:
                        gruppo = str_g
                        break

            if gruppo is not None:
                parti = cel_str.split()
                cognome = parti[0] if len(parti) > 0 else cel_str

                if gruppo == "A" and cognome not in turno_a:
                    turno_a.append(cognome)
                elif gruppo == "B" and cognome not in turno_b:
                    turno_b.append(cognome)

                if "FANTAZZINI" in cel_str:
                    if gruppo == "A" and "FANTAZZINI" not in turno_a:
                        turno_a.append("FANTAZZINI")
                    elif gruppo == "B" and "FANTAZZINI" not in turno_b:
                        turno_b.append("FANTAZZINI")

    return turno_a, turno_b

def estrai_dati_giorno(percorso_ods, nome_foglio_giorno):
    global _CACHE_ODS
    if not _CACHE_ODS:
        inizializza_cache_ods(percorso_ods)

    turno_a, turno_b = carica_anagrafica_turni(percorso_ods)

    foglio_target = next((s for s in _CACHE_ODS.keys() if str(s).strip() == str(nome_foglio_giorno).strip()), None)
    if not foglio_target:
        return turno_a, turno_b

    df_giorno = _CACHE_ODS[foglio_target]
    matrice_giorno = df_giorno.astype(str).to_numpy()

    # Lettura Cella B2 (riga 0, colonna 1) in modalità pura
    indicatore_b2 = ""
    if matrice_giorno.shape[0] > 0 and matrice_giorno.shape[1] > 1:
        indicatore_b2 = matrice_giorno[0, 1].strip().upper()

    if "TURNO A" in indicatore_b2 or "TURNO:A" in indicatore_b2 or indicatore_b2 == "A":
        op_mattina, op_pomeriggio = turno_a, turno_b
    elif "TURNO B" in indicatore_b2 or "TURNO:B" in indicatore_b2 or indicatore_b2 == "B":
        op_mattina, op_pomeriggio = turno_b, turno_a
    else:
        op_mattina, op_pomeriggio = turno_a, turno_b

    esclusi = set()
    tutti_ops = set(turno_a + turno_b)

    # Scansione matrice per assenze reali
    num_righe, num_colonne = matrice_giorno.shape
    for r in range(num_righe):
        for c in range(num_colonne):
            cel_upper = matrice_giorno[r, c].strip().upper()
            if cel_upper and cel_upper != "NAN" and "PI" not in cel_upper:
                for op in tutti_ops:
                    if op in cel_upper:
                        if any(motivo in cel_upper for motivo in MOTIVI_ASSENZA_REALE):
                            esclusi.add(op)

    disp_mattina = [op for op in op_mattina if op not in esclusi and op not in OPERATORI_ESCLUSI_SEMPRE]
    disp_pomeriggio = [op for op in op_pomeriggio if op not in esclusi and op not in OPERATORI_ESCLUSI_SEMPRE]

    return disp_mattina, disp_pomeriggio