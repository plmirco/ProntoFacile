def aggiorna_stadera(coppie_pi, totali_df, orari_df, coppie_df):
    """Aggiorna la Stadera in modo sicuro senza errori di indicizzazione su DataFrame vuoti."""
    for ops, orario in coppie_pi:
        for op in ops:
            # 1. Aggiornamento Totali PI
            if op not in totali_df.index:
                totali_df.loc[op, 'Totale_PI'] = 0
            totali_df.loc[op, 'Totale_PI'] += 1

            # 2. Aggiornamento Fasce Orarie
            if orario not in orari_df.columns:
                orari_df[orario] = 0
            if op not in orari_df.index:
                orari_df.loc[op] = 0
            
            val_orario = orari_df.loc[op, orario]
            orari_df.loc[op, orario] = (0 if pd.isna(val_orario) else val_orario) + 1

        # 3. Aggiornamento Matrice Coppie (corretto per evitare ValueError)
        if len(ops) >= 2:
            op1, op2 = ops[0], ops[1]
            
            for o in [op1, op2]:
                # Assegna la colonna se non esiste
                if o not in coppie_df.columns:
                    coppie_df[o] = 0
                # Assegna l'indice/riga se non esiste
                if o not in coppie_df.index:
                    coppie_df.loc[o, :] = 0

            val_c1 = coppie_df.loc[op1, op2]
            val_c2 = coppie_df.loc[op2, op1]
            
            coppie_df.loc[op1, op2] = (0 if pd.isna(val_c1) else val_c1) + 1
            coppie_df.loc[op2, op1] = (0 if pd.isna(val_c2) else val_c2) + 1
