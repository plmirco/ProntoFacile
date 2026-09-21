# app.py
import streamlit as st
import pandas as pd
import tempfile
import os
import io
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

# Sidebar: Controllo Stadera
with st.sidebar:
    st.header("📊 Gestione Stadera")
    
    if st.button("🔄 Azzera Storico Stadera"):
        st.session_state.totali_df = pd.DataFrame(columns=['Totale_PI'])
        st.session_state.orari_df = pd.DataFrame()
        st.session_state.coppie_df = pd.DataFrame()
        st.success("Storico Stadera azzerato!")

    st.markdown("---")
    st.subheader("📈 Contatori Attuali")
    if not st.session_state.totali_df.empty:
        st.dataframe(st.session_state.totali_df.sort_values(by="Totale_PI", ascending=False), use_container_width=True)
        
        buffer_stadera = io.BytesIO()
        with pd.ExcelWriter(buffer_stadera, engine='openpyxl') as writer:
            st.session_state.totali_df.to_excel(writer, sheet_name="Totali_PI")
            if not st.session_state.orari_df.empty:
                st.session_state.orari_df.to_excel(writer, sheet_name="Fasce_Orarie")
            if not st.session_state.coppie_df.empty:
                st.session_state.coppie_df.to_excel(writer, sheet_name="Matrice_Coppie")
        
        st.download_button(
            label="📥 Scarica Report Stadera (Excel)",
            data=buffer_stadera.getvalue(),
            file_name="Report_Stadera_Contatori.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.caption("Nessun dato registrato nella Stadera.")

uploaded_file = st.file_uploader("1. Carica il file .ods della settimana", type=["ods"])

if uploaded_file is not None:
    if 'ods_bytes' not in st.session_state or st.session_state.get('file_name') != uploaded_file.name:
        st.session_state.ods_bytes = uploaded_file.getvalue()
        st.session_state.file_name = uploaded_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ods") as tmp_file:
        tmp_file.write(st.session_state.ods_bytes)
        tmp_path = tmp_file.name

    try:
        _CACHE_ODS.clear()
        xl = pd.read_excel(tmp_path, sheet_name=None, engine='odf')
        fogli_disponibili = [str(sheet).strip() for sheet in xl.keys() if str(sheet).strip().lower() != 'dati']
        
        st.subheader("2. Seleziona i Giorni dal File")
        giorni_selezionati = st.multiselect(
            "Giorni/Fogli da elaborare:",
            options=fogli_disponibili,
            default=fogli_disponibili
        )

        st.markdown("---")
        
        if st.button("🚀 CALCOLA TABELLONE COMPLETO", type="primary", use_container_width=True):
            if not giorni_selezionati:
                st.error("Seleziona almeno un giorno dal menu sopra!")
            else:
                nomi_settimana = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]
                righe_export = []

                for idx, g in enumerate(giorni_selezionati):
                    giorno_nome = nomi_settimana[idx % len(nomi_settimana)]
                    disp_m, disp_p = estrai_dati_giorno(tmp_path, g)
                    
                    ris, anomalie = genera_turni_giorno(
                        disp_m, disp_p, giorno_nome, 
                        st.session_state.totali_df, 
                        st.session_state.orari_df, 
                        st.session_state.coppie_df
                    )

                    st.markdown(f"## 📌 FOGLIO {g} — {giorno_nome}")
                    
                    if anomalie:
                        for anom in anomalie:
                            st.warning(f"⚠️ {anom}")

                    col_m, col_p = st.columns(2)

                    with col_m:
                        st.success("### ☀️ MATTINA")
                        st.markdown("#### 🚨 Pronto Intervento (PI)")
                        if ris["MATTINA_PI"]:
                            for ops, orario in ris["MATTINA_PI"]:
                                st.write(f"⏱️ **{orario}** — 👤 " + " & 👤 ".join(ops))
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "MATTINA", "Tipo": "Pronto Intervento", "Orario/Note": orario, "Operatori": " & ".join(ops)})
                        else:
                            st.caption("Nessun servizio PI assegnato.")
                        
                        st.markdown("#### 调度 Servizio Ordinario")
                        if ris["MATTINA_ORD"]:
                            for ops, note in ris["MATTINA_ORD"]:
                                st.write(f"🔹 **{note}** — 👤 " + " & 👤 ".join(ops))
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "MATTINA", "Tipo": "Servizio Ordinario", "Orario/Note": note, "Operatori": " & ".join(ops)})

                    with col_p:
                        st.info("### 🌙 POMERIGGIO")
                        st.markdown("#### 🚨 Pronto Intervento (PI)")
                        if ris["POMERIGGIO_PI"]:
                            for ops, orario in ris["POMERIGGIO_PI"]:
                                st.write(f"⏱️ **{orario}** — 👤 " + " & 👤 ".join(ops))
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "POMERIGGIO", "Tipo": "Pronto Intervento", "Orario/Note": orario, "Operatori": " & ".join(ops)})
                        else:
                            st.caption("Nessun servizio PI assegnato.")
                        
                        st.markdown("#### 🚓 Servizio Ordinario")
                        if ris["POMERIGGIO_ORD"]:
                            for ops, note in ris["POMERIGGIO_ORD"]:
                                st.write(f"🔹 **{note}** — 👤 " + " & 👤 ".join(ops))
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "POMERIGGIO", "Tipo": "Servizio Ordinario", "Orario/Note": note, "Operatori": " & ".join(ops)})

                    st.divider()

                # Generazione file Excel finale
                if righe_export:
                    df_export = pd.DataFrame(righe_export)
                    buffer_turni = io.BytesIO()
                    with pd.ExcelWriter(buffer_turni, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name="Tabellone_Turni")
                    
                    st.success("✅ Tabellone calcolato e Stadera aggiornata!")
                    st.download_button(
                        label="📥 SCARICA TABELLONE TURNI COMPLETO (EXCEL)",
                        data=buffer_turni.getvalue(),
                        file_name="Tabellone_Turni_PI.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
