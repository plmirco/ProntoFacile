# ods_reader.py
import pandas as pd
import re
import random
import datetime

try:
    from config_rules import OPERATORI_ESCLUSI_SEMPRE
except ImportError:
    OPERATORI_ESCLUSI_SEMPRE = []

_CACHE_ODS = {}

# ANAGRAFICA UFFICIALE RIGIDA (49 OPERATORI)
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

ORARI_PI_MATTINA = ["07:00", "07:00", "07:30", "08:00"]
ORARI_PI_POMERIGGIO = ["13:00", "13:30", "14:00", "14:00"]

MAPPA_MEMBRI = {}
for op in GRUPPO_A_REALE + GRUPPO_B_REALE:
    parti = op.upper().split()
    cognome_solido = re.sub(r'[^A-Z]', '', parti[0])
    stringa_intera = re.sub(r'[^A-Z]', '', op.upper())
    if cognome_solido and len(cognome_solido) >= 3:
        MAPPA_MEMBRI[cognome_solido] = op
    if stringa_intera:
        MAPPA_MEMBRI[stringa_intera] = op

def inizializza_cache_ods(percorso_ods):
    global _CACHE_ODS
    _CACHE_ODS.clear()
    _CACHE_ODS = pd.read_excel(percorso_ods, sheet_name=None, engine='odf')

def pulisci_stringa(valore):
    if pd.isna(valore):
        return ""
    if isinstance(valore, (datetime.time, datetime.datetime)):
        return valore.strftime("%H:%M")
    val_str = str(valore).strip().upper()
    if val_str in ["NAN", "NONE", "UNNAMED", "---", "--", "-"]:
        return ""
    return val_str

def carica_anagrafica_turni(percorso_ods=None):
    return list(GRUPPO_A_REALE), list(GRUPPO_B_REALE)

def trova_operatore_match(testo_cella):
    if not testo_cella:
        return None
    testo_pulito = re.sub(r'[^A-Z\s]', '', testo_cella.upper()).strip()
    parole = testo_pulito.split()
    
    for p in parole:
        p_solida = re.sub(r'[^A-Z]', '', p)
        if len(p_solida) >= 3 and p_solida in MAPPA_MEMBRI:
            return MAPPA_MEMBRI[p_solida]
            
    intera = re.sub(r'[^A-Z]', '', testo_pulito)
    if intera in MAPPA_MEMBRI:
        return MAPPA_MEMBRI[intera]
        
    return None

def normalizza_orario_cella(val_i):
    """Pulisce la cella specifica dell'orario (Colonna I / Indice 8)."""
    if not val_i:
        return ""
    
    # Se è già in formato HH:MM o HH.MM
    m = re.search(r'\b([01]?\d|2[0-3])[\:\.]([0-5]\d)\b', val_i)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    
    # Se è espresso solo come cifra oraria (es. "22" o "19" o "7")
    m_ora = re.search(r'\b([01]?\d|2[0-3])\b', val_i)
    if m_ora:
        ora = int(m_ora.group(1))
        return f"{ora:02d}:00"
        
    return ""

def classifica_turno_orario(orario_str):
    if not orario_str:
        return "MATTINA"
    
    numeri = re.findall(r'\b\d{1,2}\b', orario_str)
    if numeri:
        ora = int(numeri[0])
        if ora >= 22 or ora <= 8:
            return "MATTINA"
        elif 12 <= ora <= 21:
            return "POMERIGGIO"
    return "MATTINA"

def crea_stadera_vuota():
    tutti_ops = GRUPPO_A_REALE + GRUPPO_B_REALE
    colonne = ["OPERATORE", "TOT_PI", "PI_07:00", "PI_07:30", "PI_08:00", "PI_13:00", "PI_13:30", "PI_14:00"]
    dati = [[op, 0, 0, 0, 0, 0, 0, 0] for op in tutti_ops]
    return pd.DataFrame(dati, columns=colonne)

def estrai_dati_giorno(percorso_ods, nome_foglio_giorno):
    global _CACHE_ODS
    if not _CACHE_ODS:
        inizializza_cache_ods(percorso_ods)

    turno_a, turno_b = carica_anagrafica_turni()

    target_clean = re.sub(r'[^0-9A-Z]', '', str(nome_foglio_giorno).upper())
    
    foglio_target = None
    for k in _CACHE_ODS.keys():
        k_clean = re.sub(r'[^0-9A-Z]', '', str(k).upper())
        if target_clean == k_clean or target_clean in k_clean:
            foglio_target = k
            break
    
    if not foglio_target:
        return [], [], [], [], []

    df_giorno = _CACHE_ODS[foglio_target].copy()

    # Riempiamo le celle unificate per Servizi (Col H / Indice 7) e Orari (Col I / Indice 8)
    if df_giorno.shape[1] > 7:
        df_giorno.iloc[:, 7] = df_giorno.iloc[:, 7].ffill()
    if df_giorno.shape[1] > 8:
        df_giorno.iloc[:, 8] = df_giorno.iloc[:, 8].ffill()

    matrice_giorno = df_giorno.to_numpy()

    # Determinazione Squadra Montante da Cella B2
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
            if cel_b and "FERIE" not in cel_b and "MALATTIE" not in cel_b and "TURNO" not in cel_b:
                match = trova_operatore_match(cel_b)
                if match:
                    assenti.add(match)

    # 2. Scansione Servizi Particolari (Colonne H-M)
    for r in range(num_righe):
        cel_servizio = pulisci_stringa(matrice_giorno[r, 7]) if num_colonne > 7 else ""
        cel_orario_grezzo = pulisci_stringa(matrice_giorno[r, 8]) if num_colonne > 8 else ""

        # Ignoriamo le intestazioni di tabella
        if "SERVIZI COMANDATI" in cel_servizio or "TIPO DI SERVIZIO" in cel_servizio:
            continue

        orario_effettivo = normalizza_orario_cella(cel_orario_grezzo)

        # Cerca l'operatore reale dell'anagrafica nelle colonne M, L, K, J (da destra a sinistra per priorità sostituti)
        operatore_effettivo = None
        for col_idx in [12, 11, 10, 9]:
            if num_colonne > col_idx:
                val_op = pulisci_stringa(matrice_giorno[r, col_idx])
                if val_op and not any(k in val_op for k in ["OPERATORE", "CAMBIO"]):
                    match = trova_operatore_match(val_op)
                    if match:
                        operatore_effettivo = match
                        break

        if operatore_effettivo and cel_servizio:
            turno_op = classifica_turno_orario(orario_effettivo)
            
            if not any(item[0] == operatore_effettivo for item in servizi_speciali_assegnati):
                servizi_speciali_assegnati.append((operatore_effettivo, cel_servizio, orario_effettivo, turno_op))
                if turno_op == "MATTINA":
                    op_impegnati_mattina.add(operatore_effettivo)
                else:
                    op_impegnati_pomeriggio.add(operatore_effettivo)

    disp_mattina = [op for op in squadra_mattina if op not in assenti and op not in OPERATORI_ESCLUSI_SEMPRE and op not in op_impegnati_mattina]
    disp_pomeriggio = [op for op in squadra_pomeriggio if op not in assenti and op not in OPERATORI_ESCLUSI_SEMPRE and op not in op_impegnati_pomeriggio]

    spec_m = [item for item in servizi_speciali_assegnati if item[3] == "MATTINA"]
    spec_p = [item for item in servizi_speciali_assegnati if item[3] == "POMERIGGIO"]

    return disp_mattina, disp_pomeriggio, spec_m, spec_p, sorted(list(assenti))

def genera_coppie_pi_con_stadera(disponibili, df_stadera, turno="MATTINA"):
    ops = list(disponibili)
    df_s = df_stadera.copy()

    ops_ordinati = sorted(ops, key=lambda x: df_s.loc[df_s["OPERATORE"] == x, "TOT_PI"].values[0] if x in df_s["OPERATORE"].values else 0)

    fantazzini_op = next((op for op in ops_ordinati if "FANTAZZINI" in op), None)
    if fantazzini_op:
        ops_ordinati.remove(fantazzini_op)

    pattuglie_pi = []
    orari_disponibili = list(ORARI_PI_MATTINA) if turno == "MATTINA" else list(ORARI_PI_POMERIGGIO)

    def scegli_orario_equo(op1, op2, orari_list):
        best_orario = orari_list[0]
        min_score = 9999
        for orario in set(orari_list):
            col_name = f"PI_{orario}"
            c1 = df_s.loc[df_s["OPERATORE"] == op1, col_name].values[0] if (op1 in df_s["OPERATORE"].values and col_name in df_s.columns) else 0
            c2 = df_s.loc[df_s["OPERATORE"] == op2, col_name].values[0] if (op2 in df_s["OPERATORE"].values and col_name in df_s.columns) else 0
            score = c1 + c2
            if score < min_score:
                min_score = score
                best_orario = orario
        return best_orario

    if fantazzini_op and ops_ordinati:
        partner = ops_ordinati.pop(0)
        orario = scegli_orario_equo(fantazzini_op, partner, orari_disponibili)
        orari_disponibili.remove(orario)
        pattuglie_pi.append({"servizio": f"Pronto Intervento ({orario})", "orario": orario, "componenti": [fantazzini_op, partner]})

    while orari_disponibili and len(ops_ordinati) >= 2:
        op1 = ops_ordinati.pop(0)
        op2 = ops_ordinati.pop(0)
        orario = scegli_orario_equo(op1, op2, orari_disponibili)
        orari_disponibili.remove(orario)
        pattuglie_pi.append({"servizio": f"Pronto Intervento ({orario})", "orario": orario, "componenti": [op1, op2]})

    altre_coppie = []
    idx_pattuglia = 1
    random.shuffle(ops_ordinati)
    while len(ops_ordinati) >= 2:
        op1 = ops_ordinati.pop(0)
        op2 = ops_ordinati.pop(0)
        altre_coppie.append({"servizio": f"Pattuglia Territorio {idx_pattuglia}", "componenti": [op1, op2]})
        idx_pattuglia += 1

    if ops_ordinati:
        spaiato = ops_ordinati.pop(0)
        if altre_coppie:
            altre_coppie[-1]["componenti"].append(spaiato)
        elif pattuglie_pi:
            pattuglie_pi[0]["componenti"].append(spaiato)
        else:
            altre_coppie.append({"servizio": "Pattuglia Singola/Supporto", "componenti": [spaiato]})

    for p in pattuglie_pi:
        orario = p["orario"]
        col_orario = f"PI_{orario}"
        for comp in p["componenti"]:
            if comp in df_s["OPERATORE"].values:
                df_s.loc[df_s["OPERATORE"] == comp, "TOT_PI"] += 1
                if col_orario in df_s.columns:
                    df_s.loc[df_s["OPERATORE"] == comp, col_orario] += 1

    return pattuglie_pi, altre_coppie, df_s
