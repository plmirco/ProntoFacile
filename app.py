# app.py
import streamlit as st
import pandas as pd
import tempfile
from ods_reader import estrai_dati_giorno, carica_anagrafica_turni
from scheduler_engine import genera_turni_giorno

st.set_page_config(page_title="Gestione Turni PI", layout="wide")

st.title("🚓 Gestione Turni Pronto Intervento")

# Upload del file ODS direttamente dal browser
file_ods = st.file_uploader("Carica il file .ods della settimana", type=["ods"])

if file_ods is not None:
    # Salva temporaneamente il file caricato
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ods") as tmp:
        tmp.write(file_ods.getvalue())
        percorso_tmp = tmp.name

    st.success("File ODS caricato con successo!")

    if st.button("🚀 Calcola Turni Settimana"):
        # Esegue la logica di calcolo già esistente
        st.subheader("Risultati Turni")
        
        # Esempio di iterazione sui giorni dal 12 al 17
        giorni = ["12", "13", "14", "15", "16", "17"]
        
        for g in giorni:
            disp_m, disp_p = estrai_dati_giorno(percorso_tmp, g)
            # Qui si invoca genera_turni_giorno(...)
            st.write(f"### Giorno {g}")
            st.write(f"**Disponibili Mattina:** {', '.join(disp_m)}")
            st.write(f"**Disponibili Pomeriggio:** {', '.join(disp_p)}")
            st.markdown("---")