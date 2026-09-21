# app.py
import streamlit as st
import pandas as pd
import tempfile
import os
import io
from ods_reader import estrai_dati_giorno, carica_anagrafica_turni, _CACHE_ODS
from scheduler_engine import genera_turni_giorno

st.set_page_config(page_title="Gestione Turni P.I.", page_icon="🚓", layout="wide")

st.title("🚓 Gestione Turni Pronto Intervento & Tabellone")

# Inizializzazione dello stato della sessione per la Stadera
if 'totali_df' not in st.session_state:
    st.session_state.totali_df = pd.DataFrame(columns=['Totale_PI'])
if 'orari_df' not in st.session_state:
    st.session_state.orari_df = pd.DataFrame()
if 'coppie_df' not in st.session_state:
    st.session_state.coppie_df = pd.DataFrame()

uploaded_file = st.file_uploader("1. Carica il file .ods del mese", type=["ods"])

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
        fogli_numerici = [f for f in fogli_disponibili if f.isdigit()]
        
        st.subheader("2. Imposta l'Intervallo dei Giorni")

        if fogli_numerici:
            fogli_ordinati = sorted([int(f) for f in fogli_numerici])
            min_g, max_g = fogli_ordinati[0], fogli_ordinati[-1]

            inizio, fine = st.slider(
                "Seleziona il periodo (Da giorno ... A giorno):",
                min_value=min_g,
                max_value=max_g,
                value=(5 if min_g <= 5 <= max_g else min_g, 10 if min_g <= 10 <= max_g else min_g + 5)
            )

            giorni_selezionati = [str(g) for g in range(inizio, fine + 1) if str(g) in fogli_disponibili]
            st.info(f"📅 Giorni selezionati ({len(giorni_selezionati)} giorni): **dal {inizio} al {fine}**")
        else:
            giorni_selezionati = st.multiselect("Seleziona i fogli da elaborare:", options=fogli_disponibili, default=fogli_disponibili)

        st.markdown("---")
        
        if st.button("🚀 CALCOLA TABELLONE GIORNALIERO", type="primary", use_container_width=True):
            if not giorni_selezionati:
                st.error("Nessun giorno valido selezionato!")
            else:
                nomi_settimana = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]
                righe_export = []

                for idx, g in enumerate(giorni_selezionati):
                    giorno_nome = nomi_settimana[idx % len(nomi_settimana)]
                    
                    disp_m, disp_p, spec_m, spec_p, assenti_giorno = estrai_dati_giorno(tmp_path, g)
                    
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
                        st.markdown("#### 🚨 Pronto Intervento (PI - Mattina)")
                        if ris["MATTINA_PI"]:
                            for ops, orario in ris["MATTINA_PI"]:
                                st.write(f"⏱️ **{orario}** — 👤 " + " & 👤 ".join(ops))
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "MATTINA", "Tipo": "PI", "Orario/Note": orario, "Operatori": " & ".join(ops)})
                        else:
                            st.caption("Nessun PI assegnato.")
                        
                        st.markdown("#### 🚓 Servizio Ordinario (Mattina)")
                        if ris["MATTINA_ORD"]:
                            for ops, note in ris["MATTINA_ORD"]:
                                st.write(f"🔹 **{note}** — 👤 " + " & 👤 ".join(ops))
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "MATTINA", "Tipo": "Ordinario", "Orario/Note": note, "Operatori": " & ".join(ops)})

                        if spec_m:
                            st.markdown("#### 👤 Servizi Singoli (Mattina)")
                            for op in spec_m:
                                st.write(f"🔸 **Servizio Singolo** — 👤 {op}")
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "MATTINA", "Tipo": "Servizio Singolo", "Orario/Note": "Singolo", "Operatori": op})

                    with col_p:
                        st.info("### 🌙 POMERIGGIO")
                        st.markdown("#### 🚨 Pronto Intervento (PI - Pomeriggio)")
                        if ris["POMERIGGIO_PI"]:
                            for ops, orario in ris["POMERIGGIO_PI"]:
                                st.write(f"⏱️ **{orario}** — 👤 " + " & 👤 ".join(ops))
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "POMERIGGIO", "Tipo": "PI", "Orario/Note": orario, "Operatori": " & ".join(ops)})
                        else:
                            st.caption("Nessun PI assegnato.")
                        
                        st.markdown("#### 🚓 Servizio Ordinario (Pomeriggio)")
                        if ris["POMERIGGIO_ORD"]:
                            for ops, note in ris["POMERIGGIO_ORD"]:
                                st.write(f"🔹 **{note}** — 👤 " + " & 👤 ".join(ops))
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "POMERIGGIO", "Tipo": "Ordinario", "Orario/Note": note, "Operatori": " & ".join(ops)})

                        if spec_p:
                            st.markdown("#### 👤 Servizi Singoli (Pomeriggio)")
                            for op in spec_p:
                                st.write(f"🔸 **Servizio Singolo** — 👤 {op}")
                                righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "POMERIGGIO", "Tipo": "Servizio Singolo", "Orario/Note": "Singolo", "Operatori": op})

                    if assenti_giorno:
                        st.warning(f"🚫 **Operatori Assenti nel Giorno {g}:** " + ", ".join(assenti_giorno))
                        for op_ass in assenti_giorno:
                            righe_export.append({"Giorno": g, "Giorno_Settimana": giorno_nome, "Turno": "NON DISPONIBILE", "Tipo": "Assente", "Orario/Note": "Assente", "Operatori": op_ass})

                    st.divider()

                if righe_export:
                    df_export = pd.DataFrame(righe_export)
                    buffer_turni = io.BytesIO()
                    with pd.ExcelWriter(buffer_turni, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name="Tabellone_Turni")
                    
                    st.success("✅ Calcolo completato!")
                    st.download_button(
                        label=f"📥 SCARICA EXCEL TABELLONE (DAL {giorni_selezionati[0]} AL {giorni_selezionati[-1]})",
                        data=buffer_turni.getvalue(),
                        file_name=f"Tabellone_Turni_{giorni_selezionati[0]}_al_{giorni_selezionati[-1]}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# Rendering Sidebar PERMANENTE (Posizionata in fondo per riflettere sempre i dati aggiornati)
with st.sidebar:
    st.header("📊 Gestione Stadera")
    if st.button("🔄 Azzera Storico Stadera"):
        st.session_state.totali_df = pd.DataFrame(columns=['Totale_PI'])
        st.session_state.orari_df = pd.DataFrame()
        st.session_state.coppie_df = pd.DataFrame()
        st.rerun()

    st.markdown("---")
    st.subheader("📈 Contatori Attuali P.I.")
    
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
            label="📥 SCARICA REPORT STADERA",
            data=buffer_stadera.getvalue(),
            file_name="Report_Stadera_Contatori.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("Nessun servizio P.I. ancora registrato nella Stadera.")
