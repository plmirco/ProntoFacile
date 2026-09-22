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

# LISTA AGENTI IN ADDESTRAMENTO (INCOMPATIBILI TRA LORO)
AGENTI_ADDESTRAMENTO = ["VISANI", "PARADISO", "MANTEGNA", "MAZZINI", "ZAVARELLA"]

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

def estrai_orario_da_stringhe(testo_servizio, testo_orario):
    unione = f"{testo_orario} {testo_servizio}"
    m = re.search(r'\b([01]?\d|2[0-3])[\:\.]([0-5]\d)\b', unione)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    m_ora = re.search(r'\b(22|23|00|01|02|03|04|05|06|07|08|12|13|14|15|16|17|18|19|20|21)\b', unione)
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

def ottieni_operatori_notturni_giorno(percorso_ods, giorno_target_str):
    global _CACHE_ODS
    if not _CACHE_ODS:
        inizializza_cache_ods(percorso_ods)
    
    target_clean = re.sub(r'[^0-9A-Z]', '', str(giorno_target_str).upper())
    foglio_target = None
    for k in _CACHE_ODS.keys():
        k_clean = re.sub(r'[^0-9A-Z]', '', str(k).upper())
        if target_clean == k_clean or target_clean in k_clean:
            foglio_target = k
            break
            
    if not foglio_target:
        return set()

    df_giorno = _CACHE_ODS[foglio_target]
    matrice = df_giorno.to_numpy()
    num_righe, num_colonne = matrice.shape
    ops_notte = set()

    servizio_corrente = ""
    orario_corrente = ""

    for r in range(num_righe):
        cel_servizio = pulisci_stringa(matrice[r, 7]) if num_colonne > 7 else ""
        cel_orario_grezzo = pulisci_stringa(matrice[r, 8]) if num_colonne > 8 else ""

        if cel_servizio and "SERVIZI COMANDATI" not in cel_servizio:
            servizio_corrente = cel_servizio

        orario_estratto = estrai_orario_da_stringhe(cel_servizio, cel_orario_grezzo)
        if orario_estratto:
            orario_corrente = orario_estratto

        operatore_effettivo = None
        for col_idx in [12, 11, 10, 9]:
            if num_colonne > col_idx:
                val_op = pulisci_stringa(matrice[r, col_idx])
                if val_op and not any(k in val_op for k in ["OPERATORE", "CAMBIO"]):
                    match = trova_operatore_match(val_op)
                    if match:
                        operatore_effettivo = match
                        break

        if operatore_effettivo:
            numeri = re.findall(r'\b\d{1,2}\b', orario_corrente)
            if numeri:
                ora = int(numeri[0])
                if ora >= 22 or ora <= 2:
                    ops_notte.add(operatore_effettivo)

    return ops_notte

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
        return [], [], [], [], [], [], [], []

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
    servizi_speciali_assegnati = []
    reperibili_a = []
    reperibili_b = []
    richieste_particolari = []
    
    op_impegnati_mattina = set()
    op_impegnati_pomeriggio = set()
    
    num_righe, num_colonne = matrice_giorno.shape

    # 1. Scansione Assenti in Colonna B
    for r in range(num_righe):
        if num_colonne > 1:
            cel_b = pulisci_stringa(matrice_giorno[r, 1])
            if cel_b and not any(k in cel_b for k in ["FERIE", "MALATTIE", "TURNO", "MATTINA", "POMERIGGIO", "REPERIB"]):
                match_ass = trova_operatore_match(cel_b)
                if match_ass:
                    assenti.add(match_ass)

    # 2. Scansione Distinta per Reperibilità A e Reperibilità B
    for r in range(num_righe):
        for c in range(num_colonne):
            testo_cel = pulisci_stringa(matrice_giorno[r, c])
            
            tipo_rep = None
            if ("REPERIB" in testo_cel or "REP" in testo_cel):
                if " B" in testo_cel or "B" in testo_cel.split():
                    tipo_rep = "B"
                elif " A" in testo_cel or "A" in testo_cel.split() or "REPERIBILITA" in testo_cel or "REPERIBILITÀ" in testo_cel:
                    tipo_rep = "A"

            if tipo_rep:
                for offset_r in range(0, 15):
                    for offset_c in range(0, 3):
                        r_chk = r + offset_r
                        c_chk = c + offset_c
                        if r_chk < num_righe and c_chk < num_colonne:
                            val_chk = pulisci_stringa(matrice_giorno[r_chk, c_chk])
                            match_op = trova_operatore_match(val_chk)
                            if match_op:
                                if tipo_rep == "A" and match_op not in reperibili_a and match_op not in reperibili_b:
                                    reperibili_a.append(match_op)
                                elif tipo_rep == "B" and match_op not in reperibili_b and match_op not in reperibili_a:
                                    reperibili_b.append(match_op)

    # 3. Scansione Richieste Particolari Operatori
    for r in range(num_righe):
        for c in range(num_colonne):
            testo_cel = pulisci_stringa(matrice_giorno[r, c])
            if "RICHIESTE" in testo_cel and "PARTICOLARI" in testo_cel:
                for offset_r in range(1, 15):
                    r_chk = r + offset_r
                    if r_chk < num_righe:
                        val_op_c = pulisci_stringa(matrice_giorno[r_chk, c]) if c < num_colonne else ""
                        val_note_c = pulisci_stringa(matrice_giorno[r_chk, c + 1]) if (c + 1) < num_colonne else ""
                        
                        match_op = trova_operatore_match(val_op_c)
                        if not match_op:
                            match_op = trova_operatore_match(val_note_c)
                            
                        if match_op:
                            nota_testo = val_note_c if val_note_c and match_op not in val_note_c else val_op_c
                            if not any(item[0] == match_op for item in richieste_particolari):
                                richieste_particolari.append((match_op, nota_testo))

    # 4. Scansione Servizi Particolari
    servizio_corrente = ""
    orario_corrente = ""

    for r in range(num_righe):
        cel_servizio = pulisci_stringa(matrice_giorno[r, 7]) if num_colonne > 7 else ""
        cel_orario_grezzo = pulisci_stringa(matrice_giorno[r, 8]) if num_colonne > 8 else ""

        if cel_servizio and not any(k in cel_servizio for k in ["SERVIZI COMANDATI", "TIPO DI SERVIZIO"]):
            servizio_corrente = cel_servizio

        orario_estratto = estrai_orario_da_stringhe(cel_servizio, cel_orario_grezzo)
        if orario_estratto:
            orario_corrente = orario_estratto

        operatore_effettivo = None
        for col_idx in [12, 11, 10, 9]:
            if num_colonne > col_idx:
                val_op = pulisci_stringa(matrice_giorno[r, col_idx])
                if val_op and not any(k in val_op for k in ["OPERATORE", "CAMBIO"]):
                    match = trova_operatore_match(val_op)
                    if match:
                        operatore_effettivo = match
                        break

        if operatore_effettivo:
            desc_servizio = servizio_corrente if servizio_corrente else "SERVIZIO SPECIALE"
            orario_effettivo = orario_corrente if orario_corrente else "07:00"
            turno_op = classifica_turno_orario(orario_effettivo)
            
            if not any(item[0] == operatore_effettivo for item in servizi_speciali_assegnati):
                servizi_speciali_assegnati.append((operatore_effettivo, desc_servizio, orario_effettivo, turno_op))
                if turno_op == "MATTINA":
                    op_impegnati_mattina.add(operatore_effettivo)
                else:
                    op_impegnati_pomeriggio.add(operatore_effettivo)

    # 5. Controllo Notte Giorno Successivo
    try:
        giorno_num = int(re.sub(r'\D', '', str(nome_foglio_giorno)))
        giorno_succ_str = str(giorno_num + 1)
        ops_notte_domani = ottieni_operatori_notturni_giorno(percorso_ods, giorno_succ_str)
        
        for op in ops_notte_domani:
            if op in squadra_pomeriggio and op not in assenti and op not in op_impegnati_pomeriggio:
                squadra_pomeriggio.remove(op)
                if op not in squadra_mattina:
                    squadra_mattina.append(op)
    except Exception:
        pass

    disp_mattina = [op for op in squadra_mattina if op not in assenti and op not in OPERATORI_ESCLUSI_SEMPRE and op not in op_impegnati_mattina]
    disp_pomeriggio = [op for op in squadra_pomeriggio if op not in assenti and op not in OPERATORI_ESCLUSI_SEMPRE and op not in op_impegnati_pomeriggio]

    spec_m = [item for item in servizi_speciali_assegnati if item[3] == "MATTINA"]
    spec_p = [item for item in servizi_speciali_assegnati if item[3] == "POMERIGGIO"]

    return disp_mattina, disp_pomeriggio, spec_m, spec_p, sorted(list(assenti)), reperibili_a, reperibili_b, richieste_particolari

def e_addestramento(op_nome):
    return any(cad in op_nome.upper() for cad in AGENTI_ADDESTRAMENTO)

def sono_incompatibili(op1, op2):
    o1_upper = op1.upper()
    o2_upper = op2.upper()
    if e_addestramento(o1_upper) and e_addestramento(o2_upper):
        return True
    if ("FANTAZZINI" in o1_upper and "BARTOLI" in o2_upper) or ("BARTOLI" in o1_upper and "FANTAZZINI" in o2_upper):
        return True
    return False

def seleziona_operatore_pesato(lista_candidati, df_s, operatore_riferimento=None):
    candidati_validi = []
    for op in lista_candidati:
        if operatore_riferimento and sono_incompatibili(operatore_riferimento, op):
            continue
        candidati_validi.append(op)
        
    if not candidati_validi:
        return None

    punteggi = []
    for op in candidati_validi:
        tot = df_s.loc[df_s["OPERATORE"] == op, "TOT_PI"].values[0] if op in df_s["OPERATORE"].values else 0
        punteggi.append(tot)

    max_p = max(punteggi) if punteggi else 0
    pesi = [(max_p - p + 1) ** 2 for p in punteggi]
    
    scelto = random.choices(candidati_validi, weights=pesi, k=1)[0]
    return scelto

def genera_coppie_pi_con_stadera(disponibili, df_stadera, turno="MATTINA"):
    ops = list(disponibili)
    df_s = df_stadera.copy()

    # OPERATORI ESCLUSI DALLA COPPIA (ANGELINI L. e SASSU B.)
    angelini_op = next((op for op in ops if "ANGELINI" in op), None)
    if angelini_op:
        ops.remove(angelini_op)

    sassu_op = next((op for op in ops if "SASSU" in op), None)
    if sassu_op:
        ops.remove(sassu_op)

    fantazzini_op = next((op for op in ops if "FANTAZZINI" in op), None)
    if fantazzini_op:
        ops.remove(fantazzini_op)

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

    # 1. FANTAZZINI G. (Priorità assoluta al PI + Partner casuale equilibrato)
    if fantazzini_op and ops and orari_disponibili:
        partner = seleziona_operatore_pesato(ops, df_s, operatore_riferimento=fantazzini_op)
        if partner:
            ops.remove(partner)
            orario = scegli_orario_equo(fantazzini_op, partner, orari_disponibili)
            orari_disponibili.remove(orario)
            pattuglie_pi.append({"servizio": f"Pronto Intervento ({orario})", "orario": orario, "componenti": [fantazzini_op, partner]})

    # 2. ALTRI PRONTI INTERVENTO
    while orari_disponibili and len(ops) >= 2:
        op1 = seleziona_operatore_pesato(ops, df_s)
        if not op1:
            break
        ops.remove(op1)

        op2 = seleziona_operatore_pesato(ops, df_s, operatore_riferimento=op1)
        if not op2:
            ops.append(op1)
            break
        ops.remove(op2)

        orario = scegli_orario_equo(op1, op2, orari_disponibili)
        orari_disponibili.remove(orario)
        pattuglie_pi.append({"servizio": f"Pronto Intervento ({orario})", "orario": orario, "componenti": [op1, op2]})

    # 3. ALTRE PATTUGLIE TERRITORIO E SERVIZI SINGOLI
    altre_coppie = []
    
    if angelini_op:
        altre_coppie.append({"servizio": "Servizio Territorio Singolo / Supporto", "componenti": [angelini_op]})

    if sassu_op:
        altre_coppie.append({"servizio": "Servizio Territorio Singolo / Supporto", "componenti": [sassu_op]})

    idx_pattuglia = 1
    random.shuffle(ops)

    while len(ops) >= 2:
        op1 = ops.pop(0)
        op2_idx = None
        for i, cand in enumerate(ops):
            if not sono_incompatibili(op1, cand):
                op2_idx = i
                break
                
        if op2_idx is not None:
            op2 = ops.pop(op2_idx)
            altre_coppie.append({"servizio": f"Pattuglia Territorio {idx_pattuglia}", "componenti": [op1, op2]})
            idx_pattuglia += 1
        else:
            ops.insert(0, op1)
            break

    # 4. GESTIONE SPAIATO: Aggregato come TERZO componente ad altre pattuglie (escludendo Angelini e Sassu)
    if ops:
        for spaiato in ops:
            assegnato = False
            for p in altre_coppie:
                if "Pattuglia Territorio" in p["servizio"]:
                    if not any(k in comp for comp in p["componenti"] for k in ["ANGELINI", "SASSU"]):
                        if not any(sono_incompatibili(spaiato, comp) for comp in p["componenti"]):
                            p["componenti"].append(spaiato)
                            assegnato = True
                            break
            if not assegnato:
                altre_coppie.append({"servizio": "Pattuglia Singola/Supporto", "componenti": [spaiato]})

    # Aggiornamento Stadera
    for p in pattuglie_pi:
        orario = p["orario"]
        col_orario = f"PI_{orario}"
        for comp in p["componenti"]:
            if comp in df_s["OPERATORE"].values:
                df_s.loc[df_s["OPERATORE"] == comp, "TOT_PI"] += 1
                if col_orario in df_s.columns:
                    df_s.loc[df_s["OPERATORE"] == comp, col_orario] += 1

    return pattuglie_pi, altre_coppie, df_s

    return pattuglie_pi, altre_coppie, df_s
