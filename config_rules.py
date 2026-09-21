# config_rules.py

ORARI_MATTINA = ["07:00", "07:00", "07:30", "08:00"]
ORARI_POMERIGGIO = ["13:00", "13:30", "14:00", "14:00"]

GIORNI_SETTIMANA = ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO"]

# Operatori in addestramento (Incompatibili SOLO tra loro due insieme)
OPERATORI_ADDESTRAMENTO = ["PARADISO", "ZAVARELLA", "MAZZINI", "MANTEGNA", "VISANI"]

# REGOLA 1: Operatori totalmente ESCLUSI da OGNI Pronto Intervento
OPERATORI_ESCLUSI_SEMPRE = ["ANGELINI", "SASSU"]

# REGOLA 2: Operatore SEMPRE PRESENTE nel PI (se in servizio e non in ferie/malattia/corso/poligono)
OPERATORI_FORZATI_SEMPRE = ["FANTAZZINI"]


def verifica_vincoli_operatore(nome, giorno_settimana, turno):
    """
    Verifica l'idoneità del singolo operatore per il giorno/turno specificato.
    """
    nome_upper = nome.strip().upper()
    giorno_upper = giorno_settimana.strip().upper()

    # Esclusione permanente Angelini e Sassu
    if any(escluso in nome_upper for escluso in OPERATORI_ESCLUSI_SEMPRE):
        return False

    # Buttazzi e Molini no PI il Martedì e Mercoledì
    if nome_upper in ["BUTTAZZI", "MOLINI"] and giorno_upper in ["MARTEDÌ", "MARTEDI", "MERCOLEDÌ", "MERCOLEDI"]:
        return False

    # Farneti il Martedì solo Pomeriggio
    if nome_upper == "FARNETI" and giorno_upper in ["MARTEDÌ", "MARTEDI"] and turno != "POMERIGGIO":
        return False

    # D'Ambra il Martedì solo Mattina
    if nome_upper in ["D'AMBRA", "DAMBRA"] and giorno_upper in ["MARTEDÌ", "MARTEDI"] and turno != "MATTINA":
        return False

    # Cumero no PI il Mercoledì
    if nome_upper == "CUMERO" and giorno_upper in ["MERCOLEDÌ", "MERCOLEDI"]:
        return False

    # Ropa, Sabatino e Coccoda NO PI quando sono di Mattina
    if nome_upper in ["ROPA", "SABATINO", "COCCODA"] and turno == "MATTINA":
        return False

    return True


def verifica_coppia_valida(op1, op2):
    """
    Verifica se due operatori possono formare una coppia valida.
    - No Angelini o Sassu
    - No due operatori in addestramento insieme
    - NO FANTAZZINI + BARTOLI insieme
    """
    op1_u = op1.strip().upper()
    op2_u = op2.strip().upper()

    # 1. Blocco rigido per gli esclusi sempre
    if op1_u in OPERATORI_ESCLUSI_SEMPRE or op2_u in OPERATORI_ESCLUSI_SEMPRE:
        return False

    # 2. Due persone in addestramento NON possono fare coppia insieme
    if op1_u in OPERATORI_ADDESTRAMENTO and op2_u in OPERATORI_ADDESTRAMENTO:
        return False

    # 3. FANTAZZINI NON PUÒ MAI FARE COPPIA CON BARTOLI
    coppia = {op1_u, op2_u}
    if "FANTAZZINI" in coppia and "BARTOLI" in coppia:
        return False

    return True