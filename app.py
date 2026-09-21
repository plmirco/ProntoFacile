# app.py
import streamlit as st
import pandas as pd
import tempfile
import os
from ods_reader import estrai_dati_giorno, carica_anagrafica_turni, _CACHE_ODS
from scheduler_engine import genera_turni_giorno

st.set_page_config(page_title="Gestione Pronto Intervento", page_icon="🚓", layout="wide")

st.title("🚓 Gestione Turni Pronto Intervento")
st.markdown("Carica il file `.ods` della settimana e seleziona i giorni per generare la programmazione.")

# Inizializzazione dataframes contatori per la Stadera
if 'totali_df' not in st.session_state:
    st.session_state.totali_df = pd.DataFrame(columns=['Totale_PI'])
if 'orari_df' not in st.session_state:
    st.session_state.orari_df = pd.DataFrame()
if 'coppie_df' not in st.session_state:
    st.session_state.coppie_df = pd.DataFrame()

# Sidebar per opzioni e reset
with st.sidebar:
    st.header("⚙️ Opzioni")
    if st.button("🔄 Azzera Storico Stadera"):
        st.session_state.totali_df = pd.DataFrame(columns=['Totale_PI'])
        st.session_state.orari_df = pd.DataFrame()
        st.session_state.coppie_df = pd.DataFrame()
        st.success("Storico azzerato correttamente!")

# Upload del file ODS
uploaded_file = st.file_uploader("Scegli il file .ods della settimana", type=["ods"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ods") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        # Lettura fogli disponibili nel file
        _CACHE_ODS.clear()
        xl = pd.read_excel(tmp_path, sheet_name=None, engine='odf')
        fogli_disponibili = [str(sheet).strip() for sheet in xl.keys() if str(sheet).strip().lower() != 'dati']
        
        st.success(f"File caricato con successo! Fogli rilevati: {', '.join(fogli_disponibili)}")

        # Selezione personalizzata dei giorni
        st.subheader("📅 Selezione Giorni/Periodo")
        giorni_selezionati = st.multiselect(
            "Scegli i giorni (fogli) per cui elaborare i turni di PI:",
            options=fogli_disponibili,
            default=fogli_disponibili
        )

        if st.button("🚀 Genera Turni P.I.", type="primary"):
            if not giorni_selezionati:
                st.warning("Seleziona almeno un giorno prima di procedere.")
            else:
                st.divider()
                st.subheader("📋 Turni Generati")

                # Nomi giorni della settimana per i vincoli
                nomi_giorni_settimana = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]

                for idx, g in enumerate(giorni_selezionati):
                    giorno_nome = nomi_giorni_settimana[idx % len(nomi_giorni_settimana)]
                    
                    disp_m, disp_p = estrai_dati_giorno(tmp_path, g)
                    
                    risultati, anomalie = genera_turni_giorno(
                        disp_m, disp_p, giorno_nome, 
                        st.session_state.totali_df, 
                        st.session_state.orari_df, 
                        st.session_state.coppie_df
                    )

                    with st.expander(f"📌 **GIORNO {g} ({giorno_nome})**", expanded=True):
                        if anomalie:
                            for anom in anomalie:
                                st.error(f"⚠️ {anom}")

                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("#### ☀️ Turno Mattina")
                            if risultati["MATTINA"]:
                                for (op1, op2), orario in risultati["MATTINA"]:
                                    st.write(f"⏱️ **{orario}** — 👤 {op1} & 👤 {op2}")
                            else:
                                st.info("Nessun turno assegnato per la Mattina.")

                        with col2:
                            st.markdown("#### 🌙 Turno Pomeriggio")
                            if risultati["POMERIGGIO"]:
                                for (op1, op2), orario in risultati["POMERIGGIO"]:
                                    st.write(f"⏱️ **{orario}** — 👤 {op1} & 👤 {op2}")
                            else:
                                st.info("Nessun turno assegnato per il Pomeriggio.")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
