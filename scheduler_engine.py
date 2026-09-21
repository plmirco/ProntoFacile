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

    def seleziona_e_completa(disponibili, orari, nome_turno):
        idonei = [op for op in disponibili if op not in OPERATORI_ESCLUSI_SEMPRE and verifica_vincoli_operatore(op, giorno_nome, nome_turno)]
        
        if len(idonei) < 2:
            return [], []

        orari_disponibili = list(orari)
        idonei_rimasti = list(idonei)

        coppie_pi = []

        # --- STEP 1: GESTIONE FANTAZZINI (FORZATO MA CON ORARIO VARIABILE) ---
        if "FANTAZZINI" in idonei_rimasti:
            idonei_rimasti.remove("FANTAZZINI")
            
            # Trova compagni idonei
            candidati = [cand for cand in idonei_rimasti if verifica_coppia_valida("FANTAZZINI", cand)]
            if candidati:
                # Sceglie il compagno con meno storici insieme a Fantazzini
                candidati.sort(key=lambda x: coppie_df.loc["FANTAZZINI", x] if ("FANTAZZINI" in coppie_df.index and x in coppie_df.columns) else 0)
                compagno = candidati[0]
                idonei_rimasti.remove(compagno)

                # Sceglie l'orario meno frequentato da Fantazzini
                orario_scelto = sorted(orari_disponibili, key=lambda o: orari_df.loc["FANTAZZINI", o] if ("FANTAZZINI" in orari_df.index and o in orari_df.columns) else 0)[0]
                orari_disponibili.remove(orario_scelto)

                coppie_pi.append((("FANTAZZINI", compagno), orario_scelto))

        # --- STEP 2: COMPLETAMENTO PRONTO INTERVENTO (ALTRE COPPIE) ---
        num_coppie_pi_rimaste = min(len(orari_disponibili), len(idonei_rimasti) // 2)

        if num_coppie_pi_rimaste > 0:
            # Ordina per chi ha fatto meno PI
            idonei_rimasti.sort(key=lambda x: totali_df.loc[x, 'Totale_PI'] if x in totali_df.index else 0)
            selezionati = idonei_rimasti[:num_coppie_pi_rimaste * 2]
            
            # Aggiorna idonei restanti per il servizio ordinario
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

        # --- STEP 3: TABELLONE COMPLETO SERVIZIO ORDINARIO (RESTANTE PERSONALE) ---
        coppie_ordinario = []
        if idonei_rimasti:
            # Ordina per rotazione coppie
            random.shuffle(idonei_rimasti)
            
            # Se sono dispari, forma 1 terzetto e i restanti a coppie
            if len(idonei_rimasti) % 2 != 0 and len(idonei_rimasti) >= 3:
                terzetto = (idonei_rimasti.pop(0), idonei_rimasti.pop(0), idonei_rimasti.pop(0))
                coppie_ordinario.append((terzetto, "Servizio Ordinario (Pattuglia da 3)"))
            
            for i in range(0, len(idonei_rimasti), 2):
                if i + 1 < len(idonei_rimasti):
                    coppie_ordinario.append(((idonei_rimasti[i], idonei_rimasti[i+1]), "Servizio Ordinario"))
                else:
                    coppie_ordinario.append(((idonei_rimasti[i],), "Servizio Ordinario"))

        return coppie_pi, coppie_ordinario

    pi_m, ord_m = seleziona_e_completa(op_mattina, ORARI_MATTINA, "MATTINA")
    pi_p, ord_p = seleziona_e_completa(op_pomeriggio, ORARI_POMERIGGIO, "POMERIGGIO")

    return {
        "MATTINA_PI": pi_m,
        "MATTINA_ORD": ord_m,
        "POMERIGGIO_PI": pi_p,
        "POMERIGGIO_ORD": ord_p
    }, anomalie
