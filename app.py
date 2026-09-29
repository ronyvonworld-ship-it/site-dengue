import sqlite3
import os
import tkinter as tk
from tkinter import ttk, messagebox

ARQUIVO_DB_BAIRRO = "bairro.db"


def init_db_bairro():
    """Cria o banco de dados e a tabela de quarteirões caso não existam."""
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarteiroes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_bairro TEXT NOT NULL,
            num_quarteirao TEXT NOT NULL,
            nome_rua TEXT NOT NULL,
            num_lado TEXT NOT NULL,
            num_imovel TEXT NOT NULL,
            tipo_imovel TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def salvar_quarteirao(bairro, quarteirao, rua, lado, imovel, tipo):
    """Salva um novo registro no banco de dados bairro.db."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quarteiroes (nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (bairro, quarteirao, rua, lado, imovel, tipo))
    conn.commit()
    conn.close()


def listar_quarteiroes():
    """Retorna todos os registros salvos em bairro.db."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel FROM quarteiroes ORDER BY id DESC")
    dados = cursor.fetchall()
    conn.close()
    return dados


class JanelaQuarteiroesTkinter:
    """Interface desktop Tkinter para cadastro e visualização de quarteirões."""
    def __init__(self, root):
        self.root = root
        self.root.title("Gerenciador de Quarteirões e Imóveis")
        self.root.geometry("750x550")
        self.root.resizable(False, False)

        init_db_bairro()

        style = ttk.Style()
        style.theme_use("clam")

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Formulário
        form_frame = ttk.LabelFrame(main_frame, text=" Cadastrar Novo Imóvel / Quarteirão ", padding="10")
        form_frame.pack(fill=tk.X, pady=(0, 15))

        # Linha 0: Bairro e Quarteirão
        ttk.Label(form_frame, text="Nome do Bairro:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ent_bairro = ttk.Entry(form_frame, width=25)
        self.ent_bairro.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(form_frame, text="Nº do Quarteirão:").grid(row=0, column=2, sticky=tk.W, pady=5)
        self.ent_quarteirao = ttk.Entry(form_frame, width=15)
        self.ent_quarteirao.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # Linha 1: Rua e Lado
        ttk.Label(form_frame, text="Nome da Rua:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ent_rua = ttk.Entry(form_frame, width=25)
        self.ent_rua.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(form_frame, text="Nº Lado Quarteirão:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.ent_lado = ttk.Entry(form_frame, width=15)
        self.ent_lado.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        # Linha 2: Imóvel e Tipo
        ttk.Label(form_frame, text="Nº do Imóvel:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.ent_imovel = ttk.Entry(form_frame, width=25)
        self.ent_imovel.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(form_frame, text="Tipo do Imóvel:").grid(row=2, column=2, sticky=tk.W, pady=5)
        self.combo_tipo = ttk.Combobox(
            form_frame,
            values=["Residência", "Comércio", "Terreno Baldio", "Outro"],
            state="readonly",
            width=13
        )
        self.combo_tipo.current(0)
        self.combo_tipo.grid(row=2, column=3, padx=5, pady=5, sticky=tk.W)

        # Botão Salvar
        btn_salvar = ttk.Button(form_frame, text="Salvar Registro", command=self.cadastrar)
        btn_salvar.grid(row=3, column=0, columnspan=4, pady=10)

        # Tabela
        table_frame = ttk.LabelFrame(main_frame, text=" Registros Cadastrados ", padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "bairro", "quarteirao", "rua", "lado", "imovel", "tipo")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("bairro", text="Bairro")
        self.tree.heading("quarteirao", text="Nº Quart.")
        self.tree.heading("rua", text="Rua")
        self.tree.heading("lado", text="Lado")
        self.tree.heading("imovel", text="Nº Imóvel")
        self.tree.heading("tipo", text="Tipo")

        self.tree.column("id", width=40, anchor=tk.CENTER)
        self.tree.column("bairro", width=120)
        self.tree.column("quarteirao", width=70, anchor=tk.CENTER)
        self.tree.column("rua", width=150)
        self.tree.column("lado", width=50, anchor=tk.CENTER)
        self.tree.column("imovel", width=70, anchor=tk.CENTER)
        self.tree.column("tipo", width=110)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.carregar_dados()

    def cadastrar(self):
        bairro = self.ent_bairro.get().strip()
        quarteirao = self.ent_quarteirao.get().strip()
        rua = self.ent_rua.get().strip()
        lado = self.ent_lado.get().strip()
        imovel = self.ent_imovel.get().strip()
        tipo = self.combo_tipo.get().strip()

        if not all([bairro, quarteirao, rua, lado, imovel, tipo]):
            messagebox.showwarning("Atenção", "Preencha todos os campos!")
            return

        salvar_quarteirao(bairro, quarteirao, rua, lado, imovel, tipo)
        messagebox.showinfo("Sucesso", "Registro adicionado com sucesso!")

        # Limpa formulário
        self.ent_bairro.delete(0, tk.END)
        self.ent_quarteirao.delete(0, tk.END)
        self.ent_rua.delete(0, tk.END)
        self.ent_lado.delete(0, tk.END)
        self.ent_imovel.delete(0, tk.END)
        self.combo_tipo.current(0)

        self.carregar_dados()

    def carregar_dados(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in listar_quarteiroes():
            self.tree.insert("", tk.END, values=row)


def abrir_janela_quarteiroes():
    """Função invocada para abrir a janela Tkinter."""
    root = tk.Tk()
    app = JanelaQuarteiroesTkinter(root)
    root.mainloop()


if __name__ == "__main__":
    abrir_janela_quarteiroes()
