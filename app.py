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
    page_title="Gestione Turni, PI e Stadera",
    page_icon="🚔",
    layout="wide"
)

st.title("🚔 Gestione Turni, Pronto Intervento e Stadera")
st.markdown("---")

if "df_stadera_attuale" not in st.session_state:
    st.session_state["df_stadera_attuale"] = crea_stadera_vuota()

st.sidebar.header("📁 Caricamento File")
file_ods = st.sidebar.file_uploader("1. Carica il file .ods dei turni", type=["ods"])
file_stadera = st.sidebar.file_uploader("2. Carica la Stadera (.csv) [Opzionale]", type=["csv"])

if file_stadera is not None:
    st.session_state["df_stadera_attuale"] = pd.read_csv(file_stadera)
    st.sidebar.success("Stadera caricata correttamente!")

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
                disp_m, disp_p, spec_m, spec_p, assenti, reperibili = estrai_dati_giorno(percorso_tmp, g_str)

                # --- SEZIONE OVERRIDE MANUALE ---
                st.subheader("🔄 Modifica Manuale Turni Operatori")
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

                # --- RIQUADRO REPERIBILITÀ ---
                st.info("📞 **Operatori in Reperibilità (A e B):**")
                if reperibili:
                    elenco_rep = [f"• **{op}**: {tipo}" for op, tipo in reperibili]
                    st.write(" | ".join(elenco_rep))
                else:
                    st.caption("Nessun operatore in reperibilità registrato per questo giorno.")

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
                    pi_m, alt_m, st.session_state["df_stadera_attuale"] = genera_coppie_pi_con_stadera(
                        disp_m, st.session_state["df_stadera_attuale"], "MATTINA"
                    )
                    pi_p, alt_p, st.session_state["df_stadera_attuale"] = genera_coppie_pi_con_stadera(
                        disp_p, st.session_state["df_stadera_attuale"], "POMERIGGIO"
                    )

                    st.subheader("🚨 Tabellone Pronto Intervento Generato")
                    c_m, c_p = st.columns(2)

                    with c_m:
                        st.success("☀️ **PATTUGLIE MATTINA**")
                        st.markdown("##### 🚨 Pronti Intervento (PI):")
                        if pi_m:
                            for item in pi_m:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))
                        else:
                            st.caption("Nessun PI generato (operatori insufficienti).")

                        st.markdown("##### 🚘 Altri Servizi / Territorio:")
                        if alt_m:
                            for item in alt_m:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))
                        else:
                            st.caption("Nessuna pattuglia aggiuntiva.")

                    with c_p:
                        st.info("🌆 **PATTUGLIE POMERIGGIO**")
                        st.markdown("##### 🚨 Pronti Intervento (PI):")
                        if pi_p:
                            for item in pi_p:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))
                        else:
                            st.caption("Nessun PI generato (operatori insufficienti).")

                        st.markdown("##### 🚘 Altri Servizi / Territorio:")
                        if alt_p:
                            for item in alt_p:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))
                        else:
                            st.caption("Nessuna pattuglia aggiuntiva.")

        st.markdown("---")
        st.subheader("📊 Stadera dei PI Aggiornata")
        st.dataframe(st.session_state["df_stadera_attuale"], use_container_width=True)

        csv_data = st.session_state["df_stadera_attuale"].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Scarica Stadera Aggiornata (.CSV)",
            data=csv_data,
            file_name="stadera_pi.csv",
            mime="text/csv"
        )

    try:
        os.remove(percorso_tmp)
    except Exception:
        pass

else:
    st.info("👈 Carica il file `.ods` dalla barra laterale per iniziare.")
