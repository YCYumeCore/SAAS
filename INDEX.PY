import os
import sqlite3
import datetime as dt
from tkinter import *
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Google API
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ------------------- CONFIG -------------------
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_google_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("outros/iateste/credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

# ------------------- BANCO LOCAL -------------------
def init_db():
    conn = sqlite3.connect("barbearia.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        preco REAL
    )
    """)
    conn.commit()
    conn.close()

# ------------------- TKINTER -------------------
class BarbeariaApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Barbearia - Integrado Google Agenda")
        self.master.geometry("1000x600")

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=BOTH, expand=True)

        # Abas
        self.frame_agenda = Frame(self.notebook)
        self.frame_servicos = Frame(self.notebook)
        self.frame_relatorios = Frame(self.notebook)

        self.notebook.add(self.frame_agenda, text="Agenda")
        self.notebook.add(self.frame_servicos, text="Serviços")
        self.notebook.add(self.frame_relatorios, text="Relatórios")

        self.build_agenda()
        self.build_servicos()
        self.build_relatorios()

        # Carrega agenda e serviços
        self.carregar_agenda()
        self.carregar_servicos()

    # ------------------- Agenda -------------------
    def build_agenda(self):
        Label(self.frame_agenda, text="Agendamentos (Google Calendar)", font=("Arial", 14, "bold")).pack(pady=10)
        self.tree_agenda = ttk.Treeview(self.frame_agenda, columns=("inicio", "titulo"), show="headings")
        self.tree_agenda.heading("inicio", text="Data/Hora")
        self.tree_agenda.heading("titulo", text="Evento")
        self.tree_agenda.pack(fill=BOTH, expand=True)

        Button(self.frame_agenda, text="Atualizar Agenda", command=self.carregar_agenda).pack(pady=10)

    def carregar_agenda(self):
        try:
            service = get_google_service()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao conectar Google Agenda: {e}")
            return

        now = dt.datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        for row in self.tree_agenda.get_children():
            self.tree_agenda.delete(row)

        if not events:
            self.tree_agenda.insert("", "end", values=("Sem eventos futuros", ""))
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            self.tree_agenda.insert("", "end", values=(start, event["summary"]))

    # ------------------- Serviços -------------------
    def build_servicos(self):
        Label(self.frame_servicos, text="Cadastro de Serviços", font=("Arial", 14, "bold")).pack(pady=10)

        frm = Frame(self.frame_servicos)
        frm.pack(pady=10)
        self.entry_nome = Entry(frm, width=30)
        self.entry_nome.grid(row=0, column=0, padx=5)
        self.entry_nome.insert(0, "Nome do serviço")
        self.entry_preco = Entry(frm, width=15)
        self.entry_preco.grid(row=0, column=1, padx=5)
        self.entry_preco.insert(0, "Preço")

        Button(frm, text="Adicionar Serviço", command=self.add_servico, bg="#007acc", fg="white").grid(row=0, column=2, padx=5)

        self.tree_servicos = ttk.Treeview(self.frame_servicos, columns=("nome", "preco"), show="headings")
        self.tree_servicos.heading("nome", text="Serviço")
        self.tree_servicos.heading("preco", text="Preço (R$)")
        self.tree_servicos.pack(fill=BOTH, expand=True)

    def add_servico(self):
        try:
            nome = self.entry_nome.get()
            preco = float(self.entry_preco.get())
        except:
            messagebox.showwarning("Erro", "Digite o nome e preço corretamente!")
            return
        conn = sqlite3.connect("barbearia.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO servicos (nome, preco) VALUES (?, ?)", (nome, preco))
        conn.commit()
        conn.close()
        self.carregar_servicos()
        self.entry_nome.delete(0, END)
        self.entry_preco.delete(0, END)

    def carregar_servicos(self):
        for row in self.tree_servicos.get_children():
            self.tree_servicos.delete(row)
        conn = sqlite3.connect("barbearia.db")
        cur = conn.cursor()
        cur.execute("SELECT nome, preco FROM servicos")
        for nome, preco in cur.fetchall():
            self.tree_servicos.insert("", "end", values=(nome, preco))
        conn.close()

    # ------------------- Relatórios -------------------
    def build_relatorios(self):
        Label(self.frame_relatorios, text="Relatórios de Serviços", font=("Arial", 14, "bold")).pack(pady=10)
        Button(self.frame_relatorios, text="Gerar Gráfico", command=self.mostrar_grafico, bg="#007acc", fg="white").pack(pady=10)

    def mostrar_grafico(self):
        conn = sqlite3.connect("barbearia.db")
        cur = conn.cursor()
        cur.execute("SELECT nome, COUNT(*) FROM servicos GROUP BY nome")
        dados = cur.fetchall()
        conn.close()

        if not dados:
            messagebox.showinfo("Relatórios", "Nenhum dado disponível.")
            return

        nomes = [d[0] for d in dados]
        qtd = [d[1] for d in dados]

        fig, ax = plt.subplots()
        ax.bar(nomes, qtd, color="#007acc")
        ax.set_title("Serviços cadastrados")
        ax.set_ylabel("Quantidade")

        for widget in self.frame_relatorios.winfo_children():
            if isinstance(widget, FigureCanvasTkAgg):
                widget.get_tk_widget().destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.frame_relatorios)
        canvas.get_tk_widget().pack()
        canvas.draw()

# ------------------- MAIN -------------------
if __name__ == "__main__":
    init_db()
    root = Tk()
    app = BarbeariaApp(root)
    root.mainloop()
