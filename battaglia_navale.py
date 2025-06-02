import streamlit as st
import random
import time
import openai 

openai.api_key = "sk-proj-1guHFW1yJ8YCPCdVkamYf8Ox7dbQPfBCqOflwwvwDMamD9vnsN02Plkl6qXmOh1iowzrb1V0wT3BlbkFJNYeAL2WMlzqV4n17O94V40dkSHnaVlSzMbCfYN43u8nB30ICe3GEFWyDQx3SXgvWUqL7cXWAYA" # <--- SOSTITUISCI CON LA TUA CHIAVE API

# Costanti di gioco
ROWS, COLS = 10, 10
NAVI_NOMI = {
    "Portaerei": 6,
    "Corazzata": 5,
    "Sommergibile": 4,
    "Incrociatore": 4,
    "Cacciatorpediniere": 3,
    "Guardacoste": 2,
}

# Classi del Gioco
class Cella:
    def __init__(self, r, c):
        self.r = r
        self.c = c
        self.stato = "."  # "." = acqua, "N" = nave, "X" = colpito, "O" = mancato
        self.nave = None

    def posiziona_nave(self, nave):
        self.nave = nave
        self.stato = "N"

    def attacca(self):
        if self.stato == "N":
            if self.nave.affondata():
                return "già colpito"
            self.stato = "X"
            self.nave.colpita()
            return "colpito"
        elif self.stato == ".":
            self.stato = "O"
            return "mancato"
        else: # Stato "X" o "O"
            return "già colpito"

class Nave:
    def __init__(self, nome, dimensione):
        self.nome = nome
        self.dimensione = dimensione
        self.celle = []
        self.colpi_subiti = 0

    def aggiungi_cella(self, cella):
        self.celle.append(cella)
        cella.posiziona_nave(self)

    def colpita(self):
        self.colpi_subiti += 1

    def affondata(self):
        return self.colpi_subiti >= self.dimensione

class Griglia:
    def __init__(self):
        self.celle = [[Cella(r, c) for c in range(COLS)] for r in range(ROWS)]
        self.navi = []

    def posiziona_nave(self, nave, r, c, verticale):
        if not (0 <= r < ROWS and 0 <= c < COLS):
            return False

        if verticale:
            if r + nave.dimensione > ROWS:
                return False
            for i in range(nave.dimensione):
                if self.celle[r+i][c].stato != ".":
                    return False # Cella già occupata
            for i in range(nave.dimensione):
                self.celle[r+i][c].posiziona_nave(nave)
                nave.aggiungi_cella(self.celle[r+i][c])
        else: # Orizzontale
            if c + nave.dimensione > COLS:
                return False
            for i in range(nave.dimensione):
                if self.celle[r][c+i].stato != ".":
                    return False # Cella già occupata
            for i in range(nave.dimensione):
                self.celle[r][c+i].posiziona_nave(nave)
                nave.aggiungi_cella(self.celle[r][c+i])
        self.navi.append(nave)
        return True

    def attacca(self, r, c):
        if not (0 <= r < ROWS and 0 <= c < COLS):
            return "fuori limiti"
        return self.celle[r][c].attacca()

    def tutte_affondate(self):
        return all(nave.affondata() for nave in self.navi)

class Giocatore:
    def __init__(self, nickname):
        self.nickname = nickname
        self.griglia = Griglia()

class Partita:
    def __init__(self, giocatore, computer):
        self.giocatore = giocatore
        self.computer = computer
        self.turno = "giocatore"
        self.inizio = "posizionamento"
        self.navi_da_posizionare = list(NAVI_NOMI.keys())
        self.ultimo_risultato = ""
        self.messaggio_affondamento = ""
        self.vincitore = None 

        # AI ragionata per il computer
        self.computer_modalita_caccia = False
        self.computer_colpi = []  # per ricordare celle già colpite
        self.computer_possibili_attacchi = [] # celle adiacenti a quelle già colpite da provare

    def celle_adiacenti(self, r, c):
        adiacenti = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]: # Destra, Sinistra, Giù, Su
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                adiacenti.append((nr, nc))
        return adiacenti

    def posiziona_nave_computer(self, nome, dimensione):
        while True:
            verticale = random.choice([True, False])
            r = random.randint(0, ROWS-1)
            c = random.randint(0, COLS-1)
            nave = Nave(nome, dimensione)
            if self.computer.griglia.posiziona_nave(nave, r, c, verticale):
                break

    def attacca_giocatore(self, r, c):
        self.messaggio_affondamento = "" # Resetta messaggio affondamento
        risultato = self.computer.griglia.attacca(r, c)
        self.ultimo_risultato = f"Hai **{risultato}** in **{chr(r+65)}{c+1}**"

        if risultato == "colpito":
            nave_colpita = None
            for nave in self.computer.griglia.navi:
                if (r, c) in [(cella.r, cella.c) for cella in nave.celle]:
                    nave_colpita = nave
                    break
            
            if nave_colpita and nave_colpita.affondata():
                self.messaggio_affondamento = f"Hai affondato la nave nemica: **{nave_colpita.nome}**! 🎉"
            
            self.turno = "giocatore" # Il giocatore continua a giocare se colpisce
        else: # Mancato o già colpito
            self.turno = "computer" # Passa il turno al computer
        return risultato

    def attacca_computer(self):
        self.messaggio_affondamento = "" 
        risultato = ""
        r, c = -1, -1

        player_grid_display = mostra_griglia(self.giocatore.griglia, False) # Mostra solo ciò che il computer "vede"
        
        # Stato corrente dell'AI
        ai_state = {
            "computer_modalita_caccia": self.computer_modalita_caccia,
            "computer_colpi": self.computer_colpi,
            "computer_possibili_attacchi": self.computer_possibili_attacchi
        }
        
        prompt_ai = f"""Sei un'intelligenza artificiale che gioca a battaglia navale.
La griglia del tuo avversario (il giocatore) è la seguente (A-J per righe, 1-10 per colonne):
{player_grid_display}

Legenda:
🌊 = Acqua (non ancora attaccata)
💧 = Mancato (acqua già attaccata)
🔥 = Colpito (nave colpita)

Il tuo obiettivo è affondare tutte le navi nemiche.
Regole per le tue mosse:
1. Se hai colpito una nave e non l'hai affondata, la tua prossima mossa DEVE essere una delle celle adiacenti non ancora attaccate per cercare di affondarla. Se ci sono più colpi, cerca di mantenere la linea (orizzontale o verticale).
2. Se non hai colpi precedenti da seguire o la nave è stata affondata, scegli una cella casuale non ancora attaccata (modalità "caccia libera").
3. Non attaccare mai una cella già attaccata ('🔥' o '💧').

Stato attuale della tua AI:
Hai una nave colpita: {self.computer_modalita_caccia}
Celle che hai colpito (e che non sono ancora affondate): {self.computer_colpi}
Celle adiacenti da esplorare: {self.computer_possibili_attacchi}

Suggerisci SOLO la tua prossima mossa nel formato "RigaColonna" (es. "A5" per riga A, colonna 5). Non aggiungere altro testo.
"""
        
        # Il giocatore computer tenta di usare OpenAI per la mossa
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini", # O "gpt-3.5-turbo", "gpt-4o"
                messages=[
                    {"role": "system", "content": "Sei un'AI per il gioco Battaglia Navale. Devi rispondere SOLO con una singola coordinata di attacco nel formato 'RigaColonna' (es. A5). Non aggiungere altro testo, spiegazioni o saluti. La coordinata deve essere valida e non già colpita."},
                    {"role": "user", "content": prompt_ai}
                ],
                max_tokens=5, # Abbastanza per una coordinata
                temperature=0.7 # Un po' di casualità, ma non troppa per non farla impazzire
            )
            ai_move_str = response.choices[0].message.content.strip().upper()
            
            # Parsing e validazione della mossa AI
            r_parsed, c_parsed = -1, -1
            valid_ai_move = False
            
            if len(ai_move_str) >= 2 and ai_move_str[0].isalpha() and ai_move_str[1:].isdigit():
                r_parsed = ord(ai_move_str[0]) - 65
                c_parsed = int(ai_move_str[1:]) - 1
                
                if 0 <= r_parsed < ROWS and 0 <= c_parsed < COLS:
                    # Verifica se la cella è già stata attaccata
                    if self.giocatore.griglia.celle[r_parsed][c_parsed].stato not in ["X", "O"]:
                        valid_ai_move = True
            
            if valid_ai_move:
                r, c = r_parsed, c_parsed
                risultato = self.giocatore.griglia.attacca(r, c)
            else:
                st.warning(f"L'AI ha suggerito una mossa non valida o già colpita ({ai_move_str}). Uso la logica interna di fallback.")
                r, c, risultato = self._computer_fallback_attack()

        except Exception as e:
            st.error(f"Errore durante la chiamata OpenAI: {e}. Uso la logica AI interna.")
            r, c, risultato = self._computer_fallback_attack()

        self.ultimo_risultato = f"Computer ha **{risultato}** in **{chr(r+65)}{c+1}**"

        if risultato == "colpito":
            self.computer_modalita_caccia = True
            self.computer_colpi.append((r, c))
            
            # Aggiorna le possibili_attacchi solo con celle valide e non ancora attaccate
            new_adjacent = [pos for pos in self.celle_adiacenti(r, c) 
                            if self.giocatore.griglia.celle[pos[0]][pos[1]].stato not in ["X", "O"]]
            
            # Se abbiamo più di un colpo, cerca di inferire la direzione e filtra le adiacenti
            if len(self.computer_colpi) > 1:
                # Trova la direzione (orizzontale o verticale)
                if self.computer_colpi[0][0] == self.computer_colpi[1][0]: # Orizzontale (stessa riga)
                    new_adjacent = [pos for pos in new_adjacent if pos[0] == self.computer_colpi[0][0]]
                else: # Verticale (stessa colonna)
                    new_adjacent = [pos for pos in new_adjacent if pos[1] == self.computer_colpi[0][1]]
            
            # Aggiungi le nuove celle adiacenti e rimuovi duplicati, mantenendo l'ordine
            self.computer_possibili_attacchi.extend(list(set(new_adjacent) - set(self.computer_possibili_attacchi)))
            self.computer_possibili_attacchi = sorted(list(set(self.computer_possibili_attacchi)), 
                                                       key=lambda p: min(abs(p[0]-h[0]) + abs(p[1]-h[1]) for h in self.computer_colpi))
            
            # Controlla se nave affondata
            affondata = False
            nave_colpita = None
            for nave in self.giocatore.griglia.navi:
                if (r, c) in [(cella.r, cella.c) for cella in nave.celle]:
                    nave_colpita = nave
                    if nave.affondata():
                        affondata = True
                        break

            if affondata:
                self.messaggio_affondamento = f"Il Computer ha affondato la tua nave: **{nave_colpita.nome}**! 💥"
                self.computer_modalita_caccia = False 
                self.computer_colpi.clear()
                self.computer_possibili_attacchi.clear()
                self.turno = "giocatore" # Passa il turno al giocatore dopo aver affondato
            else:
                self.turno = "computer" # Rimane il turno del computer se solo colpito e non affondato
        else: # Risultato è "mancato" o "già colpito"
            self.computer_modalita_caccia = False # Resetta in caso di mancato
            self.computer_colpi.clear()
            self.computer_possibili_attacchi.clear()
            self.turno = "giocatore" # Passa il turno al giocatore

    def _computer_fallback_attack(self):
        # Logica di attacco di fallback (se l'AI non risponde o dà errore o suggerisce una mossa non valida)
        # Priorità 1: attacca una delle possibili_attacchi se in target_mode
        if self.computer_modalita_caccia and self.computer_possibili_attacchi:
            # Filtra le possibili_attacchi che sono già state colpite
            self.computer_possibili_attacchi = [
                (r, c) for r, c in self.computer_possibili_attacchi
                if self.giocatore.griglia.celle[r][c].stato not in ["X", "O"]
            ]
            if self.computer_possibili_attacchi:
                r, c = self.computer_possibili_attacchi.pop(0) # Prendi la prima cella valida
                return r, c, self.giocatore.griglia.attacca(r, c)
            else: # Se non ci sono più possibili_attacchi valide, resetta e passa alla caccia libera
                self.computer_modalita_caccia = False
                self.computer_colpi.clear()

        # Priorità 2: attacco casuale (caccia libera)
        while True:
            r = random.randint(0, ROWS-1)
            c = random.randint(0, COLS-1)
            stato = self.giocatore.griglia.celle[r][c].stato
            if stato not in ["X", "O"]:
                return r, c, self.giocatore.griglia.attacca(r, c)


    def tutte_affondate(self):
        return all(nave.affondata() for nave in self.navi)

# --- Funzioni per l'Interfaccia Utente (Streamlit) ---

def mostra_griglia(griglia, mostra_navi):
    righe = []
    # Header con numeri delle colonne
    header = "    " + " ".join(f"{i+1:<2}" for i in range(COLS))
    righe.append(header)
    righe.append("   " + "—" * (COLS * 3 + 2)) # Spazi extra per allineamento

    for r in range(ROWS):
        riga = chr(r+65) + " | "
        for c in range(COLS):
            cella = griglia.celle[r][c]
            if cella.stato == ".":
                riga += "🌊  " # Acqua
            elif cella.stato == "N":
                riga += ("🚢  " if mostra_navi else "🌊  ") # Nave o Acqua (se non mostrata)
            elif cella.stato == "X":
                riga += "🔥  " # Colpito (fuoco)
            elif cella.stato == "O":
                riga += "💧  " # Mancato (spruzzo)
        righe.append(riga)
    return "\n".join(righe)

def input_posizionamento(nave):
    st.markdown(f"#### Posiziona la tua **{nave}** (dimensione **{NAVI_NOMI[nave]}**)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        r_str = st.text_input("Riga (A-J)", key=f"r_input_{nave}").strip().upper()
    with col2:
        c_str = st.text_input("Colonna (1-10)", key=f"c_input_{nave}").strip()
    with col3:
        # Modifica qui per includere la scelta Orizzontale/Verticale
        orientamento_str = st.radio("Orientamento", ("Verticale", "Orizzontale"), key=f"orientation_{nave}")
        verticale = (orientamento_str == "Verticale")
    
    if st.button(f"Posiziona {nave}", key=f"btn_pos_{nave}"):
        if not r_str or not c_str:
            st.error("Inserisci sia la riga che la colonna.")
            return None
        
        if not ("A" <= r_str <= "J"):
            st.error("Riga non valida. Inserisci una lettera tra A e J.")
            return None
        try:
            c_int = int(c_str) - 1
            if not (0 <= c_int < COLS):
                st.error("Colonna non valida. Inserisci un numero tra 1 e 10.")
                return None
        except ValueError:
            st.error("Colonna non valida. Inserisci un numero.")
            return None
        return (ord(r_str)-65, c_int, verticale)
    return None

# --- Main Streamlit App ---

def main():
    st.set_page_config(layout="wide", page_title="Battaglia Navale AI", page_icon="⚓️")
    st.title("⚓️ Battaglia Navale")

    # --- CSS per lo sfondo blu ---
    st.markdown(
        """
        <style>
        body {
            background-color: #007bff; /* Un bel blu mare */
        }
        .stApp {
            background-color: #007bff; /* Assicura che l'app stessa abbia lo sfondo */
        }
        /* Per rendere i container Streamlit un po' più trasparenti o con un colore che si abbini */
        .stFrame {
            background-color: rgba(255, 255, 255, 0.1); /* Sottile trasparenza bianca */
            border-radius: 10px;
            padding: 20px;
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 5rem;
            padding-right: 5rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Inizializzazione dello stato della sessione
    if "partita" not in st.session_state:
        st.session_state.nickname = ""
        st.session_state.partita = None
        st.session_state.computer_pending_action = False # Indica se il computer deve agire
        st.session_state.game_message = "" # Messaggi generici di gioco
        st.session_state.vincitore = None # Inizializza il vincitore

    # Schermata iniziale per inserire il nickname
    if not st.session_state.nickname:
        st.markdown("### Inizia la tua avventura in alto mare!")
        nickname = st.text_input("Inserisci il tuo nickname per iniziare la battaglia:")
        if st.button("Salpa! 🚀"):
            if nickname.strip():
                st.session_state.nickname = nickname.strip()
                giocatore = Giocatore(st.session_state.nickname)
                computer = Giocatore("Computer")
                partita = Partita(giocatore, computer)
                # Posiziona navi computer
                for nome, dimensione in NAVI_NOMI.items():
                    partita.posiziona_nave_computer(nome, dimensione)
                st.session_state.partita = partita
                st.rerun() # Ricarica per mostrare la fase di posizionamento
            else:
                st.error("Per favor, inserisci un nickname valido per salpare!")
        return # Termina la funzione qui per non renderizzare il resto

    partita = st.session_state.partita

    st.markdown("---")

    # Fase di posizionamento delle navi
    if partita.inizio == "posizionamento":
        st.markdown(f"### Ciao, **{st.session_state.nickname}**! È tempo di posizionare le tue navi.")
        st.markdown("Posiziona strategicamente la tua flotta sulla griglia. Ricorda, una volta posizionate non potrai più cambiarle!")

        if len(partita.navi_da_posizionare) == 0:
            partita.inizio = "gioco"
            st.success("Tutte le tue navi sono state posizionate! Che la battaglia abbia inizio! 💥")
            st.rerun() # Ricarica per mostrare la fase di gioco
        else:
            nave_corrente = partita.navi_da_posizionare[0]
            res = input_posizionamento(nave_corrente)
            if res:
                r, c, verticale = res
                nave = Nave(nave_corrente, NAVI_NOMI[nave_corrente])
                if partita.giocatore.griglia.posiziona_nave(nave, r, c, verticale):
                    st.success(f"**{nave_corrente}** posizionata con successo! ✅")
                    partita.navi_da_posizionare.pop(0)
                    # Reset input fields in session state for next ship
                    for key_prefix in [f"r_input_{nave_corrente}", f"c_input_{nave_corrente}", f"orientation_{nave_corrente}"]:
                        if key_prefix in st.session_state:
                            del st.session_state[key_prefix]
                    st.rerun() # Ricarica per mostrare il prossimo posizionamento
                else:
                    st.error("Posizionamento non valido! La nave si sovrappone o esce dalla griglia. Prova un'altra posizione. ❌")
            
            st.markdown("### La tua flotta:")
            st.code(mostra_griglia(partita.giocatore.griglia, True))

    # Fase di gioco
    elif partita.inizio == "gioco":
        st.markdown(f"### **{st.session_state.nickname}** vs **Computer**")

        col_player, col_computer = st.columns(2)

        with col_player:
            st.markdown(f"### La tua Griglia ({st.session_state.nickname})")
            st.code(mostra_griglia(partita.giocatore.griglia, True))
        
        with col_computer:
            st.markdown("### Griglia Nemica (Computer)")
            st.code(mostra_griglia(partita.computer.griglia, False))

        st.markdown("---")
        st.markdown(f"### **Turno attuale:** {partita.turno.capitalize()}")
        st.info(partita.ultimo_risultato)
        if partita.messaggio_affondamento:
            if "affondato la nave nemica" in partita.messaggio_affondamento:
                st.success(partita.messaggio_affondamento)
            else:
                st.error(partita.messaggio_affondamento)

        # Gestione del turno del computer
        # Questa logica si attiva se il computer è in attesa di agire
        if st.session_state.computer_pending_action and partita.turno == "computer":
            st.markdown("### È il turno del Computer...")
            with st.spinner("Il Computer sta pensando alla sua mossa..."):
                time.sleep(1.5) # Ritardo per UX
                partita.attacca_computer()
            
            # Controlla la vittoria dopo la mossa del computer
            if partita.giocatore.griglia.tutte_affondate():
                st.error("Game Over! Il computer ha affondato tutte le tue navi. Hai perso! 😭")
                partita.inizio = "fine"
                partita.vincitore = "computer" # Imposta il vincitore
                st.session_state.computer_pending_action = False # Partita finita, resetta
            
            st.rerun() 
            return 

        # Turno del giocatore
        if partita.turno == "giocatore":
            st.markdown("### È il tuo turno! Attacca la griglia del computer.")
            col_att_r, col_att_c = st.columns(2)
            with col_att_r:
                r_att = st.text_input("Riga attacco (A-J)", key="att_r").strip().upper()
            with col_att_c:
                c_att = st.text_input("Colonna attacco (1-10)", key="att_c").strip()
            
            if st.button("Fuoco! 🔥"):
                if not r_att or not c_att:
                    st.error("Inserisci sia la riga che la colonna per attaccare.")
                    return
                
                if not ("A" <= r_att <= "J"):
                    st.error("Riga non valida. Inserisci una lettera tra A e J.")
                    return
                try:
                    c_int_att = int(c_att) - 1
                    if not (0 <= c_int_att < COLS):
                        st.error("Colonna non valida. Inserisci un numero tra 1 e 10.")
                        return
                except ValueError:
                    st.error("Colonna non valida. Inserisci un numero.")
                    return
                
                risultato = partita.attacca_giocatore(ord(r_att)-65, c_int_att)
                
                if risultato == "già colpito":
                    st.warning("Hai già colpito questa cella. Scegli un'altra posizione per l'attacco. 💡")
                else:
                    # Reset input fields for attack
                    for key in ["att_r", "att_c"]:
                        if key in st.session_state:
                            del st.session_state[key]

                    # Controlla la vittoria dopo la mossa del giocatore
                    if partita.computer.griglia.tutte_affondate():
                        st.balloons()
                        st.success("🎉 CONGRATULAZIONI! Hai affondato tutte le navi nemiche! HAI VINTO! 🎉")
                        partita.inizio = "fine"
                        partita.vincitore = "giocatore" # Imposta il vincitore
                    
                    # Se il turno è passato al computer, attiva la sua azione pending
                    if partita.turno == "computer" and partita.inizio != "fine":
                        st.session_state.computer_pending_action = True 
                    
                    st.rerun() 

    # Fase di fine gioco
    elif partita.inizio == "fine":
        st.markdown("---")
        st.markdown("### Partita Terminata!")
        
        # Segnalazione del vincitore
        if partita.vincitore == "giocatore":
            st.balloons()
            st.success(f"🎉 CONGRATULAZIONI, **{st.session_state.nickname}**! Hai affondato tutte le navi nemiche! HAI VINTO! 🎉")
        elif partita.vincitore == "computer":
            st.error(f"😭 Game Over, **{st.session_state.nickname}**! Il computer ha affondato tutte le tue navi. Hai perso! 😭")
        else: # Caso di stato finale non ben definito (dovrebbe essere gestito dai controlli sopra)
            st.info("La partita è terminata. Nessun vincitore dichiarato.")

        st.markdown("Grazie per aver giocato!")
        if st.button("Ricomincia una nuova partita 🔄"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()