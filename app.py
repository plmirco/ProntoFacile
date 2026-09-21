# app.py
import streamlit as st
import pandas as pd
import tempfile
import os
from ods_reader import estrai_dati_giorno, carica_anagrafica_turni, _CACHE_ODS
from scheduler_engine import genera_turni_giorno

st.set_page_config(page_title="Gestione Pronto Intervento & Tabellone", page_icon="🚓", layout="wide")

st.title("🚓 Gestione Turni PI e Tabellone Giornaliero")

if 'totali_df' not in st.session_state:
    st.session_state.totali_df = pd.DataFrame(columns=['Totale_PI'])
if 'orari_df' not in st.session_state:
    st.session_state.orari_df = pd.DataFrame()
if 'coppie_df' not in st.session_state:
    st.session_state.coppie_df = pd.DataFrame()

uploaded_file = st.file_uploader("Carica il file .ods della settimana", type=["ods"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ods") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        _CACHE_ODS.clear()
        xl = pd.read_excel(tmp_path, sheet_name=None, engine='odf')
        fogli_disponibili = [str(sheet).strip() for sheet in xl.keys() if str(sheet).strip().lower() != 'dati']
        
        st.subheader("📅 Calendario & Selezione Giorni")
        st.info("I fogli trovati nel file ODS corrispondono ai giorni della settimana. Seleziona quelli che vuoi elaborare:")

        giorni_selezionati = st.multiselect(
            "Seleziona i giorni da elaborare:",
            options=fogli_disponibili,
            default=fogli_disponibili
        )

        if st.button("🚀 Calcola Tabellone Completo", type="primary"):
            st.divider()
            nomi_settimana = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]

            for idx, g in enumerate(giorni_selezionati):
                giorno_nome = nomi_settimana[idx % len(nomi_settimana)]
                disp_m, disp_p = estrai_dati_giorno(tmp_path, g)
                
                ris, anomalie = genera_turni_giorno(
                    disp_m, disp_p, giorno_nome, 
                    st.session_state.totali_df, 
                    st.session_state.orari_df, 
                    st.session_state.coppie_df
                )

                st.markdown(f"## 📌 GIORNO {g} — {giorno_nome}")
                
                col_m, col_p = st.columns(2)

                with col_m:
                    st.success("### ☀️ MATTINA")
                    st.markdown("#### 🚨 Pronto Intervento (PI)")
                    for (ops), orario in ris["MATTINA_PI"]:
                        st.write(f"⏱️ **{orario}** — 👤 " + " & 👤 ".join(ops))
                    
                    st.markdown("#### 🚓 Servizio Ordinario (Restante Squadra)")
                    for ops, note in ris["MATTINA_ORD"]:
                        st.write(f"🔹 **{note}** — 👤 " + " & 👤 ".join(ops))

                with col_p:
                    st.info("### 🌙 POMERIGGIO")
                    st.markdown("#### 🚨 Pronto Intervento (PI)")
                    for (ops), orario in ris["POMERIGGIO_PI"]:
                        st.write(f"⏱️ **{orario}** — 👤 " + " & 👤 ".join(ops))
                    
                    st.markdown("#### 🚓 Servizio Ordinario (Restante Squadra)")
                    for ops, note in ris["POMERIGGIO_ORD"]:
                        st.write(f"🔹 **{note}** — 👤 " + " & 👤 ".join(ops))

                st.divider()

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
