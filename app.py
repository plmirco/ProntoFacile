# app.py
import streamlit as st
import os
import tempfile
import pandas as pd
from ods_reader import (
    estrai_dati_giorno, carica_anagrafica_turni, 
    genera_coppie_pi_con_stadera, crea_stadera_vuota
)

st.set_page_config(
    page_title="Gestione Turni, PI e Stadera",
    page_icon="🚔",
    layout="wide"
)

st.title("🚔 Gestione Turni, Pronto Intervento e Stadera")
st.markdown("---")

# Sidebar
st.sidebar.header("📁 Caricamento File")
file_ods = st.sidebar.file_uploader("1. Carica il file .ods dei turni", type=["ods"])
file_stadera = st.sidebar.file_uploader("2. Carica la Stadera (.csv) [Opzionale]", type=["csv"])

# Gestione caricamento/creazione Stadera
if file_stadera is not None:
    df_stadera_attuale = pd.read_csv(file_stadera)
    st.sidebar.success("Stadera caricata correttamente!")
else:
    df_stadera_attuale = crea_stadera_vuota()
    st.sidebar.info("Nessuna stadera caricata: usata nuova stadera vuota.")

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
            giorno_fine = st.number_input("Al giorno", min_value=1, max_value=31, value=7)
        
        if giorno_inizio <= giorno_fine:
            giorni_scelti = [str(i) for i in range(giorno_inizio, giorno_fine + 1)]
    else:
        giorni_scelti = st.sidebar.multiselect(
            "Seleziona giorni:",
            options=tutti_giorni,
            default=["1", "2", "3", "4", "5", "6", "7"]
        )

    if st.sidebar.button("Elabora Giorni Selezionati", type="primary"):
        if not giorni_scelti:
            st.warning("Seleziona almeno un giorno.")
        else:
            tabs = st.tabs([f"Giorno {g}" for g in giorni_scelti])

            for idx, g_str in enumerate(giorni_scelti):
                with tabs[idx]:
                    disp_m, disp_p, spec_m, spec_p, assenti = estrai_dati_giorno(percorso_tmp, g_str)

                    st.warning(f"❌ **Operatori Assenti ({len(assenti)}):**")
                    if assenti:
                        st.write(", ".join(assenti))
                    else:
                        st.info("Nessun assente in Colonna B per questo giorno.")

                    st.markdown("---")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.header("☀️ Turno Mattina")
                        st.markdown(f"**Disponibili ({len(disp_m)}):**")
                        st.caption(", ".join(disp_m) if disp_m else "Nessuno")

                        st.markdown("**Servizi Comandati/Speciali:**")
                        if spec_m:
                            for op, serv, orario, _ in spec_m:
                                st.write(f"• **{op}**: {serv} ({orario})")
                        else:
                            st.write(" Nessun servizio speciale registrato.")

                    with col2:
                        st.header("🌆 Turno Pomeriggio")
                        st.markdown(f"**Disponibili ({len(disp_p)}):**")
                        st.caption(", ".join(disp_p) if disp_p else "Nessuno")

                        st.markdown("**Servizi Comandati/Speciali:**")
                        if spec_p:
                            for op, serv, orario, _ in spec_p:
                                st.write(f"• **{op}**: {serv} ({orario})")
                        else:
                            st.write(" Nessun servizio speciale registrato.")

                    st.markdown("---")

                    if st.button(f"🎲 Genera PI Equi con Stadera (Giorno {g_str})", key=f"btn_{g_str}"):
                        pi_m, alt_m, df_stadera_attuale = genera_coppie_pi_con_stadera(disp_m, df_stadera_attuale, "MATTINA")
                        pi_p, alt_p, df_stadera_attuale = genera_coppie_pi_con_stadera(disp_p, df_stadera_attuale, "POMERIGGIO")

                        st.subheader("🚨 Tabellone Pronto Intervento Generato")
                        c_m, c_p = st.columns(2)

                        with c_m:
                            st.success("☀️ **PATTUGLIE MATTINA**")
                            st.markdown("##### 🚨 Pronti Intervento (PI):")
                            for item in pi_m:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))

                            st.markdown("##### 🚘 Altri Servizi / Territorio:")
                            for item in alt_m:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))

                        with c_p:
                            st.info("🌆 **PATTUGLIE POMERIGGIO**")
                            st.markdown("##### 🚨 Pronti Intervento (PI):")
                            for item in pi_p:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))

                            st.markdown("##### 🚘 Altri Servizi / Territorio:")
                            for item in alt_p:
                                st.write(f"• **{item['servizio']}**: " + " - ".join(item["componenti"]))

            # Sezione per visualizzare e scaricare la Stadera aggiornata
            st.markdown("---")
            st.subheader("📊 Stadera dei PI Aggiornata")
            st.dataframe(df_stadera_attuale, use_container_width=True)

            csv_data = df_stadera_attuale.to_csv(index=False).encode('utf-8')
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
    
    st.markdown("---")
    st.subheader("📊 Visualizzazione / Download Stadera di Partenza Vuota")
    st.dataframe(df_stadera_attuale, use_container_width=True)
    csv_data = df_stadera_attuale.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Scarica Modello Stadera Vuoto (.CSV)",
        data=csv_data,
        file_name="stadera_pi_iniziale.csv",
        mime="text/csv"
    )
