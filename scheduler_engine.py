# scheduler_engine.py
import random
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

    cop = coppie_df.loc[op1, op2] if (op1 in coppie_df.index and op2 in coppie_df.columns) else 0
    punteggio += cop * 500

    or1 = orari_df.loc[op1, orario] if (op1 in orari_df.index and orario in orari_df.columns) else 0
    or2 = orari_df.loc[op2, orario] if (op2 in orari_df.index and orario in orari_df.columns) else 0
    punteggio += (or1 + or2) * 20

    return punteggio


def genera_turni_giorno(op_mattina, op_pomeriggio, giorno_nome, totali_df, orari_df, coppie_df):
    anomalie = []

    def seleziona_e_accoppia(disponibili, orari, nome_turno):
        idonei = [op for op in disponibili if op not in OPERATORI_ESCLUSI_SEMPRE and verifica_vincoli_operatore(op, giorno_nome, nome_turno)]
        
        if len(idonei) < 8:
            mancanti = max(0, 8 - len(idonei))
            anomalie.append(f"[{giorno_nome} - {nome_turno}] Disponibili {len(idonei)}/8. {mancanti} operatore/i in meno.")

        if len(idonei) < 2:
            return []

        coppie_finali = []
        orari_rimasti = list(orari)
        idonei_rimasti = list(idonei)

        # -------------------------------------------------------------
        # STEP 1: GARANZIA BLINDATA FANTAZZINI
        # -------------------------------------------------------------
        if "FANTAZZINI" in idonei_rimasti:
            idonei_rimasti.remove("FANTAZZINI")
            
            compagno_fantazzini = None
            for cand in idonei_rimasti:
                if verifica_coppia_valida("FANTAZZINI", cand):
                    compagno_fantazzini = cand
                    break
            
            if compagno_fantazzini:
                idonei_rimasti.remove(compagno_fantazzini)
                orario_f = orari_rimasti.pop(0)
                # La coppia di Fantazzini viene salvata IMMEDIATAMENTE
                coppie_finali.append((("FANTAZZINI", compagno_fantazzini), orario_f))

        # -------------------------------------------------------------
        # STEP 2: ABBINAMENTO DEGLI ALTRI OPERATORI
        # -------------------------------------------------------------
        num_coppie_restanti = min(len(orari_rimasti), len(idonei_rimasti) // 2)
        if num_coppie_restanti == 0:
            return coppie_finali

        idonei_rimasti.sort(key=lambda x: totali_df.loc[x, 'Totale_PI'] if x in totali_df.index else 0)
        selezionati_altri = idonei_rimasti[:num_coppie_restanti * 2]

        miglior_gruppo_restante = None
        miglior_punteggio = float('inf')

        for _ in range(300):
            temp = list(selezionati_altri)
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

            punteggio_totale = sum(
                calcola_punteggio_coppia(c[0], c[1], orari_rimasti[idx], totali_df, orari_df, coppie_df)
                for idx, c in enumerate(coppie_temp)
            )

            if punteggio_totale < miglior_punteggio:
                miglior_punteggio = punteggio_totale
                miglior_gruppo_restante = list(zip(coppie_temp, orari_rimasti[:len(coppie_temp)]))

        if miglior_gruppo_restante:
            coppie_finali.extend(miglior_gruppo_restante)
        else:
            # FALLBACK SE GLI ALTRI NON RIESCONO AD ACCOPPIARSI SENZA VIOLARE L'ADDESTRAMENTO:
            # Genera almeno le coppie possibili mantenendo Fantazzini
            for i in range(0, len(selezionati_altri) - 1, 2):
                if i//2 < len(orari_rimasti):
                    coppie_finali.append(((selezionati_altri[i], selezionati_altri[i+1]), orari_rimasti[i//2]))

        return coppie_finali

    res_m = seleziona_e_accoppia(op_mattina, ORARI_MATTINA, "MATTINA")
    res_p = seleziona_e_accoppia(op_pomeriggio, ORARI_POMERIGGIO, "POMERIGGIO")

    return {
        "MATTINA": res_m,
        "POMERIGGIO": res_p
    }, anomalie