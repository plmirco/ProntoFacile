# ods_reader.py
import pandas as pd
import re

try:
    from config_rules import OPERATORI_ESCLUSI_SEMPRE
except ImportError:
    OPERATORI_ESCLUSI_SEMPRE = []

_CACHE_ODS = {}

# ANAGRAFICA UFFICIALE RIGIDA
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

def estrai_cognome_base(nome_completo):
    pulisci = re.sub(r'[^A-Z\s]', '', nome_completo.upper().strip())
    parti = pulisci.split()
    return parti[0] if parti else ""

MAPPA_MEMBRI = {}
for op in GRUPPO_A_REALE:
    base = estrai_cognome_base(op)
    if base:
        MAPPA_MEMBRI[base] = op

for op in GRUPPO_B_REALE:
    base = estrai_cognome_base(op)
    if base:
        MAPPA_MEMBRI[base] = op

def inizializza_cache_ods(percorso_ods):
    global _CACHE_ODS
    _CACHE_ODS.clear()
    _CACHE_ODS = pd.read_excel(percorso_ods, sheet_name=None, engine='odf')

def pulisci_stringa(valore):
    if pd.isna(valore):
        return ""
    return str(valore).strip().upper()

def carica_anagrafica_turni(percorso_ods=None):
    return list(GRUPPO_A_REALE), list(GRUPPO_B_REALE)

def trova_operatore_match(testo_cella):
    if not testo_cella:
        return None
    testo_pulito = re.sub(r'[^A-Z\s]', '', testo_cella.upper())
    parole = testo_pulito.split()
    
    for p in parole:
        if len(p) >= 3 and p in MAPPA_MEMBRI:
            return MAPPA_MEMBRI[p]
    return None

def classifica_turno_orario(orario_str):
    """
    Determina se il servizio è MATTINA o POMERIGGIO in base all'orario di inizio:
    - Mattina/Notte: dalle 22 alle 8
    - Pomeriggio: dalle 12 alle 21
    """
    m = re.search(r'(\d{1,2})[:\.]?(\d{2})?', orario_str)
    if m:
        ora = int(m.group(1))
        if ora >= 22 or ora <= 8:
            return "MATTINA"
        elif 12 <= ora <= 21:
            return "POMERIGGIO"
    return "MATTINA" # Default se non viene specificato l'orario

def estrai_dati_giorno(percorso_ods, nome_foglio_giorno):
    global _CACHE_ODS
    if not _CACHE_ODS:
        inizializza_cache_ods(percorso_ods)

    turno_a, turno_b = carica_anagrafica_turni()

    target_str = pulisci_stringa(nome_foglio_giorno)
    foglio_target = next((s for s in _CACHE_ODS.keys() if pulisci_stringa(s) == target_str), None)
    
    if not foglio_target:
        return [], [], [], [], []

    df_giorno = _CACHE_ODS[foglio_target]
    matrice_giorno = df_giorno.to_numpy()

    # Determinazione Squadre Montanti dalla Cella B2
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
    servizi_speciali_assegnati = []
    
    op_impegnati_mattina = set()
    op_impegnati_pomeriggio = set()
    
    num_righe, num_colonne = matrice_giorno.shape

    # 1. Rilevazione ASSENTI in Colonna B (Indice 1)
    for r in range(num_righe):
        if num_colonne > 1:
            cel_b = pulisci_stringa(matrice_giorno[r, 1])
            if cel_b and cel_b != "NAN":
                match = trova_operatore_match(cel_b)
                if match:
                    assenti.add(match)

    # 2. Scansione Servizi Particolari a Squadra (Colonne H-M)
    servizio_attuale = ""
    orario_attuale = ""

    for r in range(num_righe):
        cel_servizio = pulisci_stringa(matrice_giorno[r, 7]) if num_colonne > 7 else ""
        cel_orario = pulisci_stringa(matrice_giorno[r, 8]) if num_colonne > 8 else ""

        if cel_servizio and cel_servizio != "NAN" and "SERVIZIO" not in cel_servizio:
            servizio_attuale = cel_servizio
            if cel_orario and cel_orario != "NAN":
                orario_attuale = cel_orario
        
        if servizio_attuale:
            operatore_effettivo = None
            
            # Cerca da M a J per dare priorità al SOSTITUTO
            for col_idx in [12, 11, 10, 9]:
                if num_colonne > col_idx:
                    val_op = pulisci_stringa(matrice_giorno[r, col_idx])
                    if val_op and val_op != "NAN":
                        match = trova_operatore_match(val_op)
                        if match:
                            operatore_effettivo = match
                            break

            if operatore_effettivo:
                # Classificazione rigida basata esclusivamente sull'orario d'inizio
                turno_op = classifica_turno_orario(orario_attuale)
                servizi_speciali_assegnati.append((operatore_effettivo, servizio_attuale, orario_attuale, turno_op))
                
                if turno_op == "MATTINA":
                    op_impegnati_mattina.add(operatore_effettivo)
                else:
                    op_impegnati_pomeriggio.add(operatore_effettivo)
            else:
                if not any(pulisci_stringa(matrice_giorno[r, c]) not in ["", "NAN"] for c in range(9, min(13, num_colonne))):
                    if not cel_servizio:
                        servizio_attuale = ""
                        orario_attuale = ""

    # Calcolo disponibilità nette per turno
    disp_mattina = [op for op in squadra_mattina if op not in assenti and op not in OPERATORI_ESCLUSI_SEMPRE and op not in op_impegnati_mattina]
    disp_pomeriggio = [op for op in squadra_pomeriggio if op not in assenti and op not in OPERATORI_ESCLUSI_SEMPRE and op not in op_impegnati_pomeriggio]

    spec_m = [item for item in servizi_speciali_assegnati if item[3] == "MATTINA"]
    spec_p = [item for item in servizi_speciali_assegnati if item[3] == "POMERIGGIO"]

    return disp_mattina, disp_pomeriggio, spec_m, spec_p, sorted(list(assenti))
