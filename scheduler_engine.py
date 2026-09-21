# scheduler_engine.py
import random
import pandas as pd
from config_rules import (
    verifica_vincoli_operatore, 
    verifica_coppia_valida, 
    ORARI_MATTINA, 
    ORARI_POMERIGGIO,
    OPERATORI_ESCLUSI_SEMPRE
)

def calcola_punteggio_coppia(op1, op2, orario, totali_df, orari_df, coppie_df):
    punteggio = 0
    tot1 = totali_df.loc[op1, 'Totale_PI'] if op1 in totali_df.index else 0
    tot2 = totali_df.loc[op2, 'Totale_PI'] if op2 in totali_df.index else 0
    punteggio += (tot1 + tot2) * 100

    cop = 0
    if op1 in coppie_df.index and op2 in coppie_df.columns:
        cop = coppie_df.loc[op1, op2]
    punteggio += cop * 500

    or1 = orari_df.loc[op1, orario] if (op1 in orari_df.index and orario in orari_df.columns) else 0
    or2 = orari_df.loc[op2, orario] if (op2 in orari_df.index and orario in orari_df.columns) else 0
    punteggio += (or1 + or2) * 20

    return punteggio

def aggiorna_stadera(coppie_pi, totali_df, orari_df, coppie_df):
    for ops, orario in coppie_pi:
        for op in ops:
            if op not in totali_df.index:
                totali_df.loc[op, 'Totale_PI'] = 0
            totali_df.loc[op, 'Totale_PI'] += 1

            if orario not in orari_df.columns:
                orari_df[orario] = 0
            if op not in orari_df.index:
                orari_df.loc[op, :] = 0
            
            val_orario = orari_df.loc[op, orario]
            orari_df.loc[op, orario] = (0 if pd.isna(val_orario) else val_orario) + 1

        if len(ops) >= 2:
            op1, op2 = ops[0], ops[1]
            for o in [op1, op2]:
                if o not in coppie_df.columns:
                    coppie_df[o] = 0
                if o not in coppie_df.index:
                    coppie_df.loc[o, :] = 0

            val_c1 = coppie_df.loc[op1, op2]
            val_c2 = coppie_df.loc[op2, op1]
            coppie_df.loc[op1, op2] = (0 if pd.isna(val_c1) else val_c1) + 1
            coppie_df.loc[op2, op1] = (0 if pd.isna(val_c2) else val_c2) + 1

def genera_turni_giorno(op_mattina, op_pomeriggio, giorno_nome, totali_df, orari_df, coppie_df):
    anomalie = []

    def elabora_squadra_turno(disponibili, orari, nome_turno):
        # Filtra vincoli singoli operatore
        idonei = [op for op in disponibili if op not in OPERATORI_ESCLUSI_SEMPRE and verifica_vincoli_operatore(op, giorno_nome, nome_turno)]
        
        if len(idonei) < 2:
            return [], []

        orari_disponibili = list(orari)
        idonei_rimasti = list(idonei)
        coppie_pi = []

        # 1. FANTAZZINI PRESENTE NEL SUO TURNO
        if "FANTAZZINI" in idonei_rimasti:
            idonei_rimasti.remove("FANTAZZINI")
            candidati = [cand for cand in idonei_rimasti if verifica_coppia_valida("FANTAZZINI", cand)]
            if candidati:
                candidati.sort(key=lambda x: coppie_df.loc["FANTAZZINI", x] if ("FANTAZZINI" in coppie_df.index and x in coppie_df.columns) else 0)
                compagno = candidati[0]
                idonei_rimasti.remove(compagno)

                orario_scelto = sorted(orari_disponibili, key=lambda o: orari_df.loc["FANTAZZINI", o] if ("FANTAZZINI" in orari_df.index and o in orari_df.columns) else 0)[0]
                orari_disponibili.remove(orario_scelto)
                coppie_pi.append((("FANTAZZINI", compagno), orario_scelto))

        # 2. ALTRE COPPIE PI
        num_coppie_pi = min(len(orari_disponibili), len(idonei_rimasti) // 2)

        if num_coppie_pi > 0:
            idonei_rimasti.sort(key=lambda x: totali_df.loc[x, 'Totale_PI'] if x in totali_df.index else 0)
            selezionati = idonei_rimasti[:num_coppie_pi * 2]
            for op in selezionati:
                idonei_rimasti.remove(op)

            miglior_gruppo = None
            miglior_punteggio = float('inf')

            for _ in range(200):
                temp = list(selezionati)
                random.shuffle(temp)
                valida = True
                coppie_temp = []
                for i in range(0, len(temp), 2):
                    op1, op2 = temp[i], temp[i+1]
                    if not verifica_coppia_valida(op1, op2):
                        valida = False
                        break
                    coppie_temp.append((op1, op2))

                if not valida:
                    continue

                punteggio_tot = sum(calcola_punteggio_coppia(c[0], c[1], orari_disponibili[idx], totali_df, orari_df, coppie_df) for idx, c in enumerate(coppie_temp))
                if punteggio_tot < miglior_punteggio:
                    miglior_punteggio = punteggio_tot
                    miglior_gruppo = list(zip(coppie_temp, orari_disponibili[:len(coppie_temp)]))

            if miglior_gruppo:
                coppie_pi.extend(miglior_gruppo)

        # 3. RESTANTE PERSONALE PER SERVIZIO ORDINARIO (COPPIE O TERZETTO)
        coppie_ordinario = []
        if idonei_rimasti:
            random.shuffle(idonei_rimasti)
            if len(idonei_rimasti) % 2 != 0 and len(idonei_rimasti) >= 3:
                terzetto = (idonei_rimasti.pop(0), idonei_rimasti.pop(0), idonei_rimasti.pop(0))
                coppie_ordinario.append((terzetto, "Pattuglia da 3"))
            
            for i in range(0, len(idonei_rimasti), 2):
                if i + 1 < len(idonei_rimasti):
                    coppie_ordinario.append(((idonei_rimasti[i], idonei_rimasti[i+1]), "Coppia Ordinario"))
                else:
                    coppie_ordinario.append(((idonei_rimasti[i],), "Singolo Ordinario"))

        aggiorna_stadera(coppie_pi, totali_df, orari_df, coppie_df)

        return coppie_pi, coppie_ordinario

    pi_m, ord_m = elabora_squadra_turno(op_mattina, ORARI_MATTINA, "MATTINA")
    pi_p, ord_p = elabora_squadra_turno(op_pomeriggio, ORARI_POMERIGGIO, "POMERIGGIO")

    return {
        "MATTINA_PI": pi_m,
        "MATTINA_ORD": ord_m,
        "POMERIGGIO_PI": pi_p,
        "POMERIGGIO_ORD": ord_p
    }, anomalie
