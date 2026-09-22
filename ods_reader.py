# ods_reader.py (MODALITÀ DIAGNOSTICA/DEBUG)
import pandas as pd
import re

_CACHE_ODS = {}

GRUPPO_A_REALE = [
    "ANGELINI L.", "ARMAROLI", "ATTI", "BELLUZZI", "BINI", "BONZI", "BRUSA", 
    "BUTTAZZI", "CATANZARO", "COCCODA", "DEL VECCHIO", "FARNETI", "FORZANO", 
    "GIULIANO", "GRONDONA", "LEONI L.", "MEI", "MOLINI", "PARADISO", "ROPA", 
    "SABATINO", "SIMONI MIRCO", "TARTARI", "ZAVARELLA"
]

GRUPPO_B_REALE = [
    "BARTOLI G.", "BONAVENTURA", "CACI", "CANTORE", "CASONI", "CUMERO", 
    "D'AMBRA", "D'AMORE", "FANTAZZINI G.", "FIORINI", "GAGLIANO", "GALLIERA", 
    "GRAZIA M.", "MAIOLINO", "MANTEGNA", "MAVIGLIA", "MAZZINI", "PELUSI", 
    "PINCIO", "PROVENZANO", "SASSU B.", "SCHETTINO", "VACCARO", "VISANI"
]

def carica_anagrafica_turni(percorso_ods=None):
    return list(GRUPPO_A_REALE), list(GRUPPO_B_REALE)

def crea_stadera_vuota():
    tutti_ops = GRUPPO_A_REALE + GRUPPO_B_REALE
    colonne = ["OPERATORE", "TOT_PI", "PI_07:00", "PI_07:30", "PI_08:00", "PI_13:00", "PI_13:30", "PI_14:00"]
    dati = [[op, 0, 0, 0, 0, 0, 0, 0] for op in tutti_ops]
    return pd.DataFrame(dati, columns=colonne)

def estrai_dati_giorno(percorso_ods, nome_foglio_giorno):
    """
    Legge il foglio e restituisce la matrice grezza per ispezione visiva.
    """
    try:
        xls = pd.read_excel(percorso_ods, sheet_name=None, engine='odf')
        foglio_target = next((s for s in xls.keys() if str(s).strip() == str(nome_foglio_giorno).strip()), None)
        
        if not foglio_target:
            return [f"Foglio '{nome_foglio_giorno}' non trovato. Fogli presenti: {list(xls.keys())}"], [], [], [], []

        df = xls[foglio_target]
        
        # Pulizia della tabella grezza per la visualizzazione debug
        debug_righe = []
        for idx, row in df.iterrows():
            valori_riga = [str(val).strip() if pd.notna(val) else "" for val in row.values]
            # Prendiamo solo le colonne da A ad M (primi 13 elementi)
            valori_cut = valori_riga[:13]
            if any(valori_cut): # se la riga non è totalmente vuota
                debug_righe.append(f"Riga {idx+1}: " + " | ".join([f"[{i}]:{v}" for i, v in enumerate(valori_cut) if v]))

        return debug_righe, list(GRUPPO_A_REALE), [], [], []

    except Exception as e:
        return [f"Errore lettura file ODS: {str(e)}"], [], [], [], []

def genera_coppie_pi_con_stadera(disponibili, df_stadera, turno="MATTINA"):
    return [], [], df_stadera
