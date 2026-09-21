# app.py
import streamlit as st
import os
import tempfile
from ods_reader import estrai_dati_giorno, carica_anagrafica_turni

st.set_page_config(
    page_title="Gestione Turni e Servizi",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Gestione Turni, Assenze e Servizi")
st.markdown("---")

# Sidebar per il caricamento file e la selezione giorno
st.sidebar.header("📁 Caricamento Dati")
file_ods = st.sidebar.file_uploader("Carica il file .ods dei turni", type=["ods"])

if file_ods is not None:
    # Salvataggio temporaneo del file inviato dall'utente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ods") as tmp_file:
        tmp_file.write(file_ods.getvalue())
        percorso_tmp = tmp_file.name

    st.sidebar.success("File caricato con successo!")

    # Selezione del giorno (foglio del mese)
    giorno_selezionato = st.sidebar.selectbox(
        "Seleziona il giorno/foglio:",
        options=[str(i) for i in range(1, 32)]
    )

    if st.sidebar.button("Elabora Giorno", type="primary"):
        disp_m, disp_p, spec_m, spec_p, assenti = estrai_dati_giorno(percorso_tmp, giorno_selezionato)

        st.subheader(f"📅 Report per il Giorno {giorno_selezionato}")

        # Sezione Assenti
        st.warning(f"❌ **Operatori Assenti ({len(assenti)}):**")
        if assenti:
            st.write(", ".join(assenti))
        else:
            st.info("Nessun assente rilevato in Colonna B per questo giorno.")

        st.markdown("---")

        # Layout a due colonne per Mattina e Pomeriggio
        col1, col2 = st.columns(2)

        with col1:
            st.header("☀️ Turno Mattina")
            st.markdown(f"**Disponibili ({len(disp_m)}):**")
            for op in disp_m:
                st.write(f"- {op}")

            st.markdown("**Servizi Particolari Mattina:**")
            if spec_m:
                for op, serv, orario, _ in spec_m:
                    st.write(f"• **{op}**: {serv} ({orario})")
            else:
                st.write(" Nessun servizio speciale registrato.")

        with col2:
            st.header("🌆 Turno Pomeriggio")
            st.markdown(f"**Disponibili ({len(disp_p)}):**")
            for op in disp_p:
                st.write(f"- {op}")

            st.markdown("**Servizi Particolari Pomeriggio:**")
            if spec_p:
                for op, serv, orario, _ in spec_p:
                    st.write(f"• **{op}**: {serv} ({orario})")
            else:
                st.write(" Nessun servizio speciale registrato.")

    # Pulizia del file temporaneo al termine dell'esecuzione
    try:
        os.remove(percorso_tmp)
    except Exception:
        pass

else:
    st.info("👈 Per iniziare, carica il file `.ods` dalla barra laterale a sinistra.")

    # Mostra l'organico di riferimento attualmente caricato nel sistema
    turno_a, turno_b = carica_anagrafica_turni()
    st.markdown("---")
    st.subheader("👥 Organico di Riferimento (Anagrafica)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Gruppo A ({len(turno_a)} operatori):**")
        st.caption(", ".join(turno_a))
    with c2:
        st.markdown(f"**Gruppo B ({len(turno_b)} operatori):**")
        st.caption(", ".join(turno_b))
