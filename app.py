# app.py
import streamlit as st
import os
import tempfile
import pandas as pd
from ods_reader import (
    estrai_dati_giorno, carica_anagrafica_turni, 
    genera_coppie_pi_con_stadera, crea_stadera_vuota,
    GRUPPO_A_REALE, GRUPPO_B_REALE
)

st.set_page_config(
    page_title="Gestione Turni, PI e Stadera Storica",
    page_icon="🚔",
    layout="wide"
)

st.title("🚔 Gestione Turni, Pronto Intervento e Registro Date PI")
st.markdown("---")

# Inizializzazione Session State per Stadera e Storico Date
if "df_stadera_attuale" not in st.session_state:
    st.session_state["df_stadera_attuale"] = crea_stadera_vuota()

if "storico_registro_pi" not in st.session_state:
    st.session_state["storico_registro_pi"] = pd.DataFrame(
        columns=["GIORNO", "TURNO", "ORARIO", "OPERATORE_1", "OPERATORE_2", "SERVIZIO"]
    )

def ricalcola_stadera_da_storico():
    """Ricalcola la Stadera totale basandosi unicamente sulle righe presenti nel Registro Date."""
    df_s = crea_stadera_vuota()
    registro = st.session_state["storico_registro_pi"]
    
    for _, row in registro.iterrows():
        orario = row["ORARIO"]
        col_orario = f"PI_{orario}" if f"PI_{orario}" in df_s.columns else None
        
        for op_col in ["OPERATORE_1", "OPERATORE_2"]:
            op = row[op_col]
            if pd.notna(op) and op in df_s["OPERATORE"].values:
                idx = df_s[df_s["OPERATORE"] == op].index[0]
                df_s.loc[idx, "TOT_PI"] += 1
                if col_orario:
                    df_s.loc[idx, col_orario] += 1
                    
    st.session_state["df_stadera_attuale"] = df_s

st.sidebar.header("📁 Caricamento File")
file_ods = st.sidebar.file_uploader("1. Carica il file .ods dei turni", type=["ods"])
file_stadera = st.sidebar.file_uploader("2. Carica la Stadera (.csv) [Opzionale]", type=["csv"])

if file_stadera is not None:
    try:
        # Tenta la lettura sia con punto e virgola che con virgola per massima compatibilità
        try:
            st.session_state["df_stadera_attuale"] = pd.read_csv(file_stadera, sep=';')
        except Exception:
            file_stadera.seek(0)
            st.session_state["df_stadera_attuale"] = pd.read_csv(file_stadera, sep=',')
        st.sidebar.success("Stadera caricata e incolonnata correttamente!")
    except Exception as e:
        st.sidebar.error(f"Errore nella lettura del file CSV: {e}")

if file_ods is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ods") as tmp_file:
        tmp_file.write(file_ods.getvalue())
        percorso_tmp = tmp_file.name

    st.sidebar.markdown("---")
    st.sidebar.header("📅 Selezione Giorni")

    tipo_selezione = st.sidebar.radio(
        "Modalità di selezione:",
        ["Intervallo di Giorni (es. 1-7)", "Giorni Singoli / Multipli Personalizzati"]
    )

    tutti_giorni = [str(i) for i in range(1, 32)]
    giorni_scelti = []

    if tipo_selezione == "Intervallo di Giorni (es. 1-7)":
        col_da, col_a = st.sidebar.columns(2)
        with col_da:
            giorno_inizio = st.number_input("Dal giorno", min_value=1, max_value=31, value=1)
        with col_a:
            giorno_fine = st.number_input("Al giorno", min_value=1, max_value=31, value=10)
        
        if giorno_inizio <= giorno_fine:
            giorni_scelti = [str(i) for i in range(giorno_inizio, giorno_fine + 1)]
    else:
        giorni_scelti = st.sidebar.multiselect(
            "Seleziona giorni:",
            options=tutti_giorni,
            default=["10"]
        )

    if giorni_scelti:
        tabs = st.tabs([f"Giorno {g}" for g in giorni_scelti])

        for idx, g_str in enumerate(giorni_scelti):
            with tabs[idx]:
                disp_m, disp_p, spec_m, spec_p, assenti, rep_a, rep_b, richieste_part = estrai_dati_giorno(percorso_tmp, g_str)

                # --- SEZIONE OVERRIDE MANUALE ---
                st.subheader("🔄 Modifica Manuale Turni Operatori per la Generazione")
                col_ov1, col_ov2 = st.columns(2)
                tutti_ops = sorted(GRUPPO_A_REALE + GRUPPO_B_REALE)
                
                with col_ov1:
                    op_da_spostare = st.selectbox("Seleziona Operatore:", ["Nessuno"] + tutti_ops, key=f"sel_op_{g_str}")
                with col_ov2:
                    nuovo_turno = st.radio("Sposta nel turno:", ["Non Modificare", "Mattina", "Pomeriggio"], key=f"rad_t_{g_str}")

                if op_da_spostare != "Nessuno" and nuovo_turno != "Non Modificare":
                    if nuovo_turno == "Mattina":
                        if op_da_spostare in disp_p:
                            disp_p.remove(op_da_spostare)
                        if op_da_spostare not in disp_m and op_da_spostare not in assenti:
                            disp_m.append(op_da_spostare)
                    elif nuovo_turno == "Pomeriggio":
                        if op_da_spostare in disp_m:
                            disp_m.remove(op_da_spostare)
                        if op_da_spostare not in disp_p and op_da_spostare not in assenti:
                            disp_p.append(op_da_spostare)
                    st.success(f"Operatore {op_da_spostare} spostato nel turno di {nuovo_turno}!")

                st.markdown("---")

                # --- SEZIONE REPERIBILITÀ A, REPERIBILITÀ B E RICHIESTE ---
                c_ra, c_rb, c_req = st.columns(3)

                with c_ra:
                    st.info("📞 **Reperibilità A:**")
                    if rep_a:
                        for op in rep_a:
                            st.write(f"• **{op}**")
                    else:
                        st.caption("Nessuno in Reperibilità A.")

                with c_rb:
                    st.info("📞 **Reperibilità B:**")
                    if rep_b:
                        for op in rep_b:
                            st.write(f"• **{op}**")
                    else:
                        st.caption("Nessuno in Reperibilità B.")

                with c_req:
                    st.subheader("📝 **Richieste Particolari:**")
                    if richieste_part:
                        for op, nota in richieste_part:
                            st.write(f"• **{op}**: {nota}")
                    else:
                        st.caption("Nessuna richiesta particolare.")

                st.warning(f"❌ **Operatori Assenti / Non Disponibili ({len(assenti)}):**")
                if assenti:
                    st.write(", ".join(assenti))
                else:
                    st.info("Nessun assente registrato per questo giorno.")

                st.markdown("---")

                col1, col2 = st.columns(2)

                with col1:
                    st.header("☀️ Turno Mattina")
                    st.markdown(f"**Disponibili per Pattuglie ({len(disp_m)}):**")
                    st.caption(", ".join(sorted(disp_m)) if disp_m else "Nessuno")

                    st.markdown("**Servizi Comandati/Speciali:**")
                    if spec_m:
                        for op, serv, orario, _ in spec_m:
                            st.write(f"• **{op}**: {serv} ({orario})")
                    else:
                        st.write("Nessun servizio speciale registrato.")

                with col2:
                    st.header("🌆 Turno Pomeriggio")
                    st.markdown(f"**Disponibili per Pattuglie ({len(disp_p)}):**")
                    st.caption(", ".join(sorted(disp_p)) if disp_p else "Nessuno")

                    st.markdown("**Servizi Comandati/Speciali:**")
                    if spec_p:
                        for op, serv, orario, _ in spec_p:
                            st.write(f"• **{op}**: {serv} ({orario})")
                    else:
                        st.write("Nessun servizio speciale registrato.")

                st.markdown("---")

                if st.button(f"🎲 Genera PI Equi con Stadera (Giorno {g_str})", key=f"btn_{g_str}"):
                    # Rimuove le vecchie registrazioni per questo giorno prima di sovrascrivere
                    df_reg = st.session_state["storico_registro_pi"]
                    df_reg = df_reg[df_reg["GIORNO"] != str(g_str)]
                    
                    pi_m, alt_m, _ = genera_coppie_pi_con_stadera(
                        disp_m, st.session_state["df_stadera_attuale"], "MATTINA"
                    )
                    pi_p, alt_p, _ = genera_coppie_pi_con_stadera(
                        disp_p, st.session_state["df_stadera_attuale"], "POMERIGGIO"
                    )

                    # Inserimento nel Registro Date Storico
                    nuove_righe = []
                    for item in pi_m:
                        comps = item["componenti"]
                        op1 = comps[0] if len(comps) > 0 else ""
                        op2 = comps[1] if len(comps) > 1 else ""
                        nuove_righe.append({
                            "GIORNO": str(g_str), "TURNO": "MATTINA", "ORARIO": item["orario"],
                            "OPERATORE_1": op1, "OPERATORE_2": op2, "SERVIZIO": item["servizio"]
                        })

                    for item in pi_p:
                        comps = item["componenti"]
                        op1 = comps[0] if len(comps) > 0 else ""
                        op2 = comps[1] if len(comps) > 1 else ""
                        nuove_righe.append({
                            "GIORNO": str(g_str), "TURNO": "POMERIGGIO", "ORARIO": item["orario"],
                            "OPERATORE_1": op1, "OPERATORE_2": op2, "SERVIZIO": item["servizio"]
                        })

                    if nuove_righe:
                        st.session_state["storico_registro_pi"] = pd.concat(
                            [df_reg, pd.DataFrame(nuove_righe)], ignore_index=True
                        )

                    # Ricalcolo rigoroso ed equo della Stadera
                    ricalcola_stadera_da_storico()

                    st.subheader("🚨 Tabellone Giornaliero Generato")
                    c_m, c_p = st.columns(2)

                    with c_m:
                        st.success("☀️ **PATTUGLIE E SERVIZI MATTINA**")
                        st.markdown("##### 🚨 Pronti Intervento (PI):")
                        if pi_m:
                            for item in pi_m:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))
                        else:
                            st.caption("Nessun PI generato.")

                        st.markdown("##### 🚘 Altri Servizi / Territorio:")
                        if alt_m:
                            for item in alt_m:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))
                        else:
                            st.caption("Nessuna pattuglia aggiuntiva.")

                        st.markdown("##### 📌 Servizi Comandati / Speciali:")
                        if spec_m:
                            for op, serv, orario, _ in spec_m:
                                st.write(f"• **{op}**: {serv} ({orario})")
                        else:
                            st.caption("Nessun servizio comandato.")

                    with c_p:
                        st.info("🌆 **PATTUGLIE E SERVIZI POMERIGGIO**")
                        st.markdown("##### 🚨 Pronti Intervento (PI):")
                        if pi_p:
                            for item in pi_p:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))
                        else:
                            st.caption("Nessun PI generato.")

                        st.markdown("##### 🚘 Altri Servizi / Territorio:")
                        if alt_p:
                            for item in alt_p:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))
                        else:
                            st.caption("Nessuna pattuglia aggiuntiva.")

                        st.markdown("##### 📌 Servizi Comandati / Speciali:")
                        if spec_p:
                            for op, serv, orario, _ in spec_p:
                                st.write(f"• **{op}**: {serv} ({orario})")
                        else:
                            st.caption("Nessun servizio comandato.")

        st.markdown("---")

        # --- SEZIONE VISUALIZZAZIONE SCHEDA PERSONALE OPERATORE E DATE PI ---
        st.subheader("🗓️ Scheda Personale Operatore & Storico Date PI")
        col_sch1, col_sch2 = st.columns([3, 7])
        
        with col_sch1:
            op_selezionato = st.selectbox("Seleziona Operatore per Storico Date:", ["Tutti gli Operatori"] + sorted(GRUPPO_A_REALE + GRUPPO_B_REALE))
            
        with col_sch2:
            reg_df = st.session_state["storico_registro_pi"]
            if op_selezionato != "Tutti gli Operatori":
                reg_filtrato = reg_df[(reg_df["OPERATORE_1"] == op_selezionato) | (reg_df["OPERATORE_2"] == op_selezionato)]
                st.markdown(f"##### Date PI svolti da **{op_selezionato}** (Totale: {len(reg_filtrato)}):")
                if not reg_filtrato.empty:
                    st.dataframe(reg_filtrato, use_container_width=True)
                else:
                    st.caption("Nessun PI registrato per questo operatore nelle date generate.")
            else:
                st.markdown("##### Registro completo di tutte le date generate:")
                st.dataframe(reg_df, use_container_width=True)

        st.markdown("---")

        # --- SEZIONE STADERA TOTALE ---
        st.subheader("📊 Stadera dei PI Aggiornata")
        st.dataframe(st.session_state["df_stadera_attuale"], use_container_width=True)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            # Esportazione ottimizzata per Excel italiano (sep=';' e utf-8-sig)
            csv_data = st.session_state["df_stadera_attuale"].to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Scarica Stadera Aggiornata (.CSV per Excel)",
                data=csv_data,
                file_name="stadera_pi.csv",
                mime="text/csv"
            )
        with col_d2:
            csv_storico = st.session_state["storico_registro_pi"].to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Scarica Registro Storico Date (.CSV per Excel)",
                data=csv_storico,
                file_name="storico_date_pi.csv",
                mime="text/csv"
            )

    try:
        os.remove(percorso_tmp)
    except Exception:
        pass

else:
    st.info("👈 Carica il file `.ods` dalla barra laterale per iniziare.")
