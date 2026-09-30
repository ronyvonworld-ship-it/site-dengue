import sqlite3
import os

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


def atualizar_quarteirao(id_reg, bairro, quarteirao, rua, lado, imovel, tipo):
    """Atualiza um registro existente pelo ID."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE quarteiroes
        SET nome_bairro = ?, num_quarteirao = ?, nome_rua = ?, num_lado = ?, num_imovel = ?, tipo_imovel = ?
        WHERE id = ?
    """, (bairro, quarteirao, rua, lado, imovel, tipo, id_reg))
    conn.commit()
    conn.close()


def excluir_quarteirao(id_reg):
    """Exclui um registro pelo ID."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quarteiroes WHERE id = ?", (id_reg,))
    conn.commit()
    conn.close()


def listar_quarteiroes(f_bairro="", f_quarteirao="", f_rua="", f_imovel="", f_tipo=""):
    """Retorna os registros aplicando filtros dinâmicos de busca."""
    init_db_bairro()
    conn = sqlite3.connect(ARQUIVO_DB_BAIRRO)
    cursor = conn.cursor()

    sql = "SELECT id, nome_bairro, num_quarteirao, nome_rua, num_lado, num_imovel, tipo_imovel FROM quarteiroes WHERE 1=1"
    params = []

    if f_bairro:
        sql += " AND nome_bairro LIKE ?"
        params.append(f"%{f_bairro.strip()}%")
    if f_quarteirao:
        sql += " AND num_quarteirao LIKE ?"
        params.append(f"%{f_quarteirao.strip()}%")
    if f_rua:
        sql += " AND nome_rua LIKE ?"
        params.append(f"%{f_rua.strip()}%")
    if f_imovel:
        sql += " AND num_imovel LIKE ?"
        params.append(f"%{f_imovel.strip()}%")
    if f_tipo and f_tipo != "Todos":
        sql += " AND tipo_imovel = ?"
        params.append(f_tipo.strip())

    sql += " ORDER BY id DESC"

    cursor.execute(sql, params)
    dados = cursor.fetchall()
    conn.close()
    return dados


def abrir_janela_quarteiroes():
    """Importa o tkinter e abre a janela gráfica apenas se for executado localmente."""
    import tkinter as tk
    from tkinter import ttk, messagebox

    class JanelaQuarteiroesTkinter:
        def __init__(self, root):
            self.root = root
            self.root.title("Gerenciador de Quarteirões e Imóveis")
            self.root.geometry("850x650")
            self.root.resizable(True, True)

            self.id_selecionado = None
            init_db_bairro()

            style = ttk.Style()
            style.theme_use("clam")

            main_frame = ttk.Frame(self.root, padding="15")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # --- Form de Cadastro / Edição ---
            form_frame = ttk.LabelFrame(main_frame, text=" Formulário (Cadastrar / Editar) ", padding="10")
            form_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(form_frame, text="Bairro:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.ent_bairro = ttk.Entry(form_frame, width=20)
            self.ent_bairro.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

            ttk.Label(form_frame, text="Nº Quart.:").grid(row=0, column=2, sticky=tk.W, pady=2)
            self.ent_quarteirao = ttk.Entry(form_frame, width=12)
            self.ent_quarteirao.grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)

            ttk.Label(form_frame, text="Rua:").grid(row=1, column=0, sticky=tk.W, pady=2)
            self.ent_rua = ttk.Entry(form_frame, width=20)
            self.ent_rua.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

            ttk.Label(form_frame, text="Nº Lado:").grid(row=1, column=2, sticky=tk.W, pady=2)
            self.ent_lado = ttk.Entry(form_frame, width=12)
            self.ent_lado.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)

            ttk.Label(form_frame, text="Nº Imóvel:").grid(row=2, column=0, sticky=tk.W, pady=2)
            self.ent_imovel = ttk.Entry(form_frame, width=20)
            self.ent_imovel.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)

            ttk.Label(form_frame, text="Tipo:").grid(row=2, column=2, sticky=tk.W, pady=2)
            self.combo_tipo = ttk.Combobox(
                form_frame,
                values=["Residência", "Comércio", "Terreno Baldio", "Outro"],
                state="readonly",
                width=11
            )
            self.combo_tipo.current(0)
            self.combo_tipo.grid(row=2, column=3, padx=5, pady=2, sticky=tk.W)

            # Botões de Ação do Formulário
            btn_box = ttk.Frame(form_frame)
            btn_box.grid(row=3, column=0, columnspan=4, pady=10)

            self.btn_salvar = ttk.Button(btn_box, text="Salvar Novo", command=self.salvar)
            self.btn_salvar.pack(side=tk.LEFT, padx=5)

            self.btn_atualizar = ttk.Button(btn_box, text="Atualizar Selecionado", command=self.atualizar, state=tk.DISABLED)
            self.btn_atualizar.pack(side=tk.LEFT, padx=5)

            self.btn_excluir = ttk.Button(btn_box, text="Excluir Selecionado", command=self.excluir, state=tk.DISABLED)
            self.btn_excluir.pack(side=tk.LEFT, padx=5)

            btn_limpar = ttk.Button(btn_box, text="Limpar Campos", command=self.limpar_formulario)
            btn_limpar.pack(side=tk.LEFT, padx=5)

            # --- Filtros de Busca ---
            filter_frame = ttk.LabelFrame(main_frame, text=" Filtros de Pesquisa ", padding="10")
            filter_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(filter_frame, text="Bairro:").grid(row=0, column=0, padx=2)
            self.f_bairro = ttk.Entry(filter_frame, width=12)
            self.f_bairro.grid(row=0, column=1, padx=2)

            ttk.Label(filter_frame, text="Quart.:").grid(row=0, column=2, padx=2)
            self.f_quarteirao = ttk.Entry(filter_frame, width=8)
            self.f_quarteirao.grid(row=0, column=3, padx=2)

            ttk.Label(filter_frame, text="Rua:").grid(row=0, column=4, padx=2)
            self.f_rua = ttk.Entry(filter_frame, width=12)
            self.f_rua.grid(row=0, column=5, padx=2)

            ttk.Label(filter_frame, text="Imóvel:").grid(row=0, column=6, padx=2)
            self.f_imovel = ttk.Entry(filter_frame, width=8)
            self.f_imovel.grid(row=0, column=7, padx=2)

            ttk.Label(filter_frame, text="Tipo:").grid(row=0, column=8, padx=2)
            self.f_tipo = ttk.Combobox(
                filter_frame,
                values=["Todos", "Residência", "Comércio", "Terreno Baldio", "Outro"],
                state="readonly",
                width=11
            )
            self.f_tipo.current(0)
            self.f_tipo.grid(row=0, column=9, padx=2)

            btn_filtrar = ttk.Button(filter_frame, text="Filtrar", command=self.carregar_dados)
            btn_filtrar.grid(row=0, column=10, padx=5)

            # --- Tabela ---
            table_frame = ttk.LabelFrame(main_frame, text=" Registros ", padding="10")
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

            # Evento ao clicar em uma linha da tabela
            self.tree.bind("<<TreeviewSelect>>", self.ao_selecionar_item)

            self.carregar_dados()

        def carregar_dados(self):
            for item in self.tree.get_children():
                self.tree.delete(item)

            dados = listar_quarteiroes(
                f_bairro=self.f_bairro.get(),
                f_quarteirao=self.f_quarteirao.get(),
                f_rua=self.f_rua.get(),
                f_imovel=self.f_imovel.get(),
                f_tipo=self.f_tipo.get()
            )
            for row in dados:
                self.tree.insert("", tk.END, values=row)

        def ao_selecionar_item(self, event):
            selecao = self.tree.selection()
            if selecao:
                item = self.tree.item(selecao[0])
                valores = item["values"]

                self.id_selecionado = valores[0]

                # Preenche o formulário com os dados da linha selecionada
                self.ent_bairro.delete(0, tk.END)
                self.ent_bairro.insert(0, valores[1])

                self.ent_quarteirao.delete(0, tk.END)
                self.ent_quarteirao.insert(0, valores[2])

                self.ent_rua.delete(0, tk.END)
                self.ent_rua.insert(0, valores[3])

                self.ent_lado.delete(0, tk.END)
                self.ent_lado.insert(0, valores[4])

                self.ent_imovel.delete(0, tk.END)
                self.ent_imovel.insert(0, valores[5])

                self.combo_tipo.set(valores[6])

                self.btn_atualizar.config(state=tk.NORMAL)
                self.btn_excluir.config(state=tk.NORMAL)

        def salvar(self):
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
            messagebox.showinfo("Sucesso", "Registro cadastrado com sucesso!")
            self.limpar_formulario()
            self.carregar_dados()

        def atualizar(self):
            if not self.id_selecionado:
                return

            bairro = self.ent_bairro.get().strip()
            quarteirao = self.ent_quarteirao.get().strip()
            rua = self.ent_rua.get().strip()
            lado = self.ent_lado.get().strip()
            imovel = self.ent_imovel.get().strip()
            tipo = self.combo_tipo.get().strip()

            if not all([bairro, quarteirao, rua, lado, imovel, tipo]):
                messagebox.showwarning("Atenção", "Preencha todos os campos!")
                return

            atualizar_quarteirao(self.id_selecionado, bairro, quarteirao, rua, lado, imovel, tipo)
            messagebox.showinfo("Sucesso", "Registro atualizado com sucesso!")
            self.limpar_formulario()
            self.carregar_dados()

        def excluir(self):
            if not self.id_selecionado:
                return

            resposta = messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir o registro selecionado?")
            if resposta:
                excluir_quarteirao(self.id_selecionado)
                messagebox.showinfo("Sucesso", "Registro excluído com sucesso!")
                self.limpar_formulario()
                self.carregar_dados()

        def limpar_formulario(self):
            self.id_selecionado = None
            self.ent_bairro.delete(0, tk.END)
            self.ent_quarteirao.delete(0, tk.END)
            self.ent_rua.delete(0, tk.END)
            self.ent_lado.delete(0, tk.END)
            self.ent_imovel.delete(0, tk.END)
            self.combo_tipo.current(0)

            self.btn_atualizar.config(state=tk.DISABLED)
            self.btn_excluir.config(state=tk.DISABLED)

    root = tk.Tk()
    app = JanelaQuarteiroesTkinter(root)
    root.mainloop()


if __name__ == "__main__":
    abrir_janela_quarteiroes()
