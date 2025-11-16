import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import sqlite3
import re
import os # --- NOVO: Para manipulação de arquivos/caminhos

class ClinicaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Clínica Vida+ (SQLite)")
        self.geometry("800x600")
        
        # --- 1. CONFIGURAÇÃO DO BANCO DE DADOS ---
        self.db_name = "dados_pacientes.db"
        self.conn = None
        self.cursor = None
        self.conectar_bd()
        self.criar_tabela_pacientes()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # --- 2. CONFIGURAÇÃO DA GUI ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")
        
        self.create_cadastro_tab()
        self.create_lista_tab()
        self.create_estatisticas_tab()

    # --- MÉTODOS DE GERENCIAMENTO DO BANCO ---
    
    def conectar_bd(self):
        """Estabelece a conexão com o arquivo SQLite."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de BD", f"Não foi possível conectar ao banco de dados: {e}")
            self.quit()

    def on_closing(self):
        """Fecha a conexão com o banco e destrói a janela."""
        if self.conn:
            self.conn.close()
        self.destroy()

    def criar_tabela_pacientes(self):
        """Cria a tabela de pacientes se ela não existir."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT NOT NULL UNIQUE,
                idade INTEGER,
                telefone TEXT
            )
        """)
        self.conn.commit()

    # --- LÓGICAS (CRUD - Create, Read, Update, Delete) ---
    
    def validar_cpf_formato(self, cpf):
        """
        Checa se o CPF tem 11 dígitos numéricos, ignorando formatação.
        (Validação de formato, não de dígitos verificadores)
        """
        # Remove quaisquer caracteres não numéricos (., -)
        cpf_numerico = re.sub(r'\D', '', cpf)
        
        if len(cpf_numerico) == 11:
            return True, cpf_numerico
        else:
            return False, ""


    def cadastrar_paciente_bd(self, nome, cpf_numerico, idade, telefone):
        """Função para adicionar paciente ao BD."""
        try:
            idade = int(idade)
            self.cursor.execute("""
                INSERT INTO pacientes (nome, cpf, idade, telefone)
                VALUES (?, ?, ?, ?)
            """, (nome, cpf_numerico, idade, telefone))
            self.conn.commit()
            return True, "Paciente cadastrado com sucesso!"
        except ValueError:
            return False, "Erro: Idade deve ser um número inteiro."
        except sqlite3.IntegrityError:
            return False, f"ERRO: Paciente com CPF {cpf_numerico} já está cadastrado."
        except Exception as e:
            return False, f"Erro ao salvar paciente: {e}"

    def formatar_cpf_exibicao(self, cpf_numerico):
        """Aplica a máscara XXX.XXX.XXX-XX para exibição na Treeview."""
        if cpf_numerico and len(cpf_numerico) == 11 and cpf_numerico.isdigit():
            return f"{cpf_numerico[:3]}.{cpf_numerico[3:6]}.{cpf_numerico[6:9]}-{cpf_numerico[9:]}"
        return cpf_numerico

    def listar_pacientes_bd(self, termo_busca=""):
        """Função para listar todos os pacientes do BD, com filtro opcional. Retorna CPF formatado."""
        if termo_busca:
            # Busca o termo (ignora maiúsculas/minúsculas) no Nome OU no CPF
            busca_param = f'%{termo_busca}%'
            self.cursor.execute("""
                SELECT nome, cpf, idade, telefone 
                FROM pacientes 
                WHERE nome LIKE ? OR cpf LIKE ? 
                ORDER BY nome
            """, (busca_param, busca_param))
        else:
            self.cursor.execute("SELECT nome, cpf, idade, telefone FROM pacientes ORDER BY nome")
            
        resultados = self.cursor.fetchall()
        
        # Formata o CPF para exibição
        pacientes_formatados = []
        for nome, cpf, idade, telefone in resultados:
            cpf_formatado = self.formatar_cpf_exibicao(cpf)
            pacientes_formatados.append((nome, cpf_formatado, idade, telefone if telefone else 'N/A'))
            
        return pacientes_formatados
        
    def remover_paciente_bd(self, cpf_formatado):
        """Função para remover paciente do BD."""
        # Remove a formatação para buscar no BD
        cpf_numerico = re.sub(r'\D', '', cpf_formatado) 
        
        self.cursor.execute("DELETE FROM pacientes WHERE cpf=?", (cpf_numerico,))
        
        if self.cursor.rowcount > 0:
            self.conn.commit()
            return True, f"Paciente com CPF {cpf_formatado} removido com sucesso."
        else:
            return False, f"Erro: Nenhum paciente encontrado com o CPF {cpf_formatado}."

    def editar_paciente_bd(self, cpf_antigo_numerico, nome, idade, telefone):
        """Atualiza os dados de um paciente no BD."""
        try:
            idade = int(idade)
            self.cursor.execute("""
                UPDATE pacientes 
                SET nome=?, idade=?, telefone=?
                WHERE cpf=?
            """, (nome, idade, telefone, cpf_antigo_numerico))
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                return True, "Dados do paciente atualizados com sucesso!"
            else:
                return False, f"Erro: Paciente não encontrado."
        except ValueError:
            return False, "Erro: Idade deve ser um número inteiro."
        except Exception as e:
            return False, f"Erro ao atualizar paciente: {e}"

    # --- NOVO: EXPORTAÇÃO DE DADOS ---
    def exportar_pacientes_para_txt(self):
        """Busca todos os pacientes e salva os dados formatados em um arquivo TXT."""
        
        # Faz uma nova busca (sem filtro) para garantir que todos os dados sejam salvos
        self.cursor.execute("SELECT nome, cpf, idade, telefone FROM pacientes ORDER BY nome")
        pacientes = self.cursor.fetchall()
        
        if not pacientes:
            messagebox.showwarning("Exportação", "Não há pacientes cadastrados para exportar.")
            return

        # Nome e caminho do arquivo de saída
        nome_arquivo = "relatorio_pacientes.txt"
        caminho_completo = os.path.join(os.getcwd(), nome_arquivo)
        
        # Prepara o cabeçalho e as linhas de dados
        linhas = []
        linhas.append("="*80)
        linhas.append("RELATÓRIO COMPLETO DE PACIENTES - CLÍNICA VIDA+")
        linhas.append(f"Data de Geração: {self.obter_data_hora_atual()}")
        linhas.append("="*80)
        linhas.append(f"{'Nome':<35} {'CPF':<15} {'Idade':<5} {'Telefone':<15}")
        linhas.append("-" * 80)
        
        for nome, cpf_num, idade, telefone in pacientes:
            cpf_formatado = self.formatar_cpf_exibicao(cpf_num)
            telefone_disp = telefone if telefone else 'N/A'
            linhas.append(f"{nome:<35} {cpf_formatado:<15} {idade:<5} {telefone_disp:<15}")
        
        linhas.append("\n" + "="*80)
        linhas.append(f"Total de Pacientes: {len(pacientes)}")
        linhas.append("="*80)

        # Salva no arquivo
        try:
            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                f.write('\n'.join(linhas))
            
            messagebox.showinfo("Exportação Concluída", 
                                f"Relatório salvo com sucesso em:\n{caminho_completo}\n\nO arquivo está pronto para impressão.")
        except Exception as e:
            messagebox.showerror("Erro de Exportação", f"Erro ao salvar o arquivo: {e}")

    def obter_data_hora_atual(self):
        """Função auxiliar para obter data e hora atual (simples)."""
        import time
        return time.strftime("%d/%m/%Y %H:%M:%S")

    # --- MÉTODOS DA GUI ---
    
    def create_cadastro_tab(self):
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text=" Cadastrar Paciente ")
        self.nome_var = tk.StringVar()
        self.cpf_var = tk.StringVar()
        self.idade_var = tk.StringVar()
        self.telefone_var = tk.StringVar()
        fields = [("Nome:", self.nome_var), ("CPF (11 dígitos, opcionalmente formatado):", self.cpf_var), ("Idade:", self.idade_var), ("Telefone:", self.telefone_var)]
        
        for i, (label_text, var) in enumerate(fields):
            ttk.Label(frame, text=label_text).grid(row=i, column=0, sticky="w", pady=5, padx=5)
            ttk.Entry(frame, textvariable=var, width=40).grid(row=i, column=1, pady=5, padx=5)
        
        ttk.Button(frame, text="Cadastrar", command=self.handle_cadastro).grid(row=len(fields), columnspan=2, pady=20)
        ttk.Button(frame, text="Remover por CPF", command=self.handle_remocao).grid(row=len(fields) + 1, columnspan=2, pady=5)
        ttk.Button(frame, text="Editar por CPF", command=self.handle_edicao).grid(row=len(fields) + 2, columnspan=2, pady=5)


    def handle_cadastro(self):
        """Coleta dados da GUI, valida o CPF e chama a função de cadastro no BD."""
        nome = self.nome_var.get().strip()
        cpf = self.cpf_var.get().strip()
        idade = self.idade_var.get().strip()
        telefone = self.telefone_var.get().strip()

        if not nome or not cpf or not idade:
             messagebox.showerror("Erro de Cadastro", "Nome, CPF e Idade são obrigatórios.")
             return
             
        valido, cpf_numerico = self.validar_cpf_formato(cpf)
        
        if not valido:
            messagebox.showerror("Erro de Cadastro", "O CPF deve conter exatamente 11 dígitos numéricos (pode usar . e -).")
            return
        
        sucesso, mensagem = self.cadastrar_paciente_bd(nome, cpf_numerico, idade, telefone)
        
        if sucesso:
            messagebox.showinfo("Sucesso", mensagem)
            self.nome_var.set(""); self.cpf_var.set(""); self.idade_var.set(""); self.telefone_var.set("")
            self.update_lista_tab() 
        else:
            messagebox.showerror("Erro de Cadastro", mensagem)

    def handle_remocao(self):
        cpf_remover_formatado = simpledialog.askstring("Remover Paciente", "Digite o CPF (com ou sem formatação) do paciente a ser removido:")
        if cpf_remover_formatado:
            sucesso, mensagem = self.remover_paciente_bd(cpf_remover_formatado)
            if sucesso:
                messagebox.showinfo("Remoção", mensagem)
                self.update_lista_tab()
            else:
                messagebox.showerror("Erro de Remoção", mensagem)

    def handle_edicao(self):
        cpf_editar_formatado = simpledialog.askstring("Editar Paciente", "Digite o CPF (com ou sem formatação) do paciente que deseja editar:")
        
        if not cpf_editar_formatado:
            return

        cpf_editar_numerico = re.sub(r'\D', '', cpf_editar_formatado)

        self.cursor.execute("SELECT nome, idade, telefone FROM pacientes WHERE cpf=?", (cpf_editar_numerico,))
        dados_atuais = self.cursor.fetchone()
        
        if not dados_atuais:
            messagebox.showerror("Edição", f"Nenhum paciente encontrado com o CPF {cpf_editar_formatado}.")
            return

        nome_atual, idade_atual, telefone_atual = dados_atuais
        
        dialog_edit = tk.Toplevel(self)
        dialog_edit.title(f"Editar: {nome_atual} (CPF: {self.formatar_cpf_exibicao(cpf_editar_numerico)})")
        dialog_edit.resizable(False, False)
        
        novo_nome_var = tk.StringVar(value=nome_atual)
        novo_idade_var = tk.StringVar(value=str(idade_atual))
        novo_telefone_var = tk.StringVar(value=telefone_atual)

        tk.Label(dialog_edit, text="Nome:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(dialog_edit, textvariable=novo_nome_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(dialog_edit, text="Idade:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(dialog_edit, textvariable=novo_idade_var, width=40).grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(dialog_edit, text="Telefone:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(dialog_edit, textvariable=novo_telefone_var, width=40).grid(row=2, column=1, padx=5, pady=5)

        def salvar_edicao():
            novo_nome = novo_nome_var.get().strip()
            nova_idade = novo_idade_var.get().strip()
            novo_telefone = novo_telefone_var.get().strip()
            
            if not novo_nome or not nova_idade:
                 messagebox.showerror("Erro de Edição", "Nome e Idade são obrigatórios.")
                 return

            sucesso, mensagem = self.editar_paciente_bd(
                cpf_editar_numerico, novo_nome, nova_idade, novo_telefone
            )
            
            if sucesso:
                messagebox.showinfo("Sucesso", mensagem)
                dialog_edit.destroy()
                self.update_lista_tab()
            else:
                messagebox.showerror("Erro de Edição", mensagem)

        ttk.Button(dialog_edit, text="Salvar Alterações", command=salvar_edicao).grid(row=3, columnspan=2, pady=10)
        ttk.Button(dialog_edit, text="Cancelar", command=dialog_edit.destroy).grid(row=4, columnspan=2, pady=5)
        
        dialog_edit.transient(self)
        dialog_edit.grab_set()
        self.wait_window(dialog_edit)

    def exibir_detalhes_selecionado(self):
        """Exibe os detalhes completos do paciente selecionado na Treeview (o 'imprimir' ativo)."""
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showwarning("Detalhes", "Selecione um paciente na lista para ver os detalhes.")
            return

        item = self.tree.item(selecao[0])
        valores = item['values']
        
        if len(valores) < 4 or (len(valores) > 0 and "Nenhum paciente" in str(valores[0])):
            messagebox.showwarning("Detalhes", "Seleção inválida. Selecione uma linha de paciente válida.")
            return

        nome, cpf, idade, telefone = valores[0], valores[1], valores[2], valores[3]
        
        detalhes = (
            f"Nome: {nome}\n"
            f"CPF: {cpf}\n"
            f"Idade: {idade} anos\n"
            f"Telefone: {telefone}"
        )
        
        messagebox.showinfo(f"Detalhes do Paciente: {nome}", detalhes)

    # --- Aba de Listagem ---
    
    def create_lista_tab(self):
        self.lista_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.lista_frame, text=" Listar Pacientes ")

        # --- SEÇÃO DE BUSCA ---
        search_frame = ttk.Frame(self.lista_frame)
        search_frame.pack(fill='x', pady=5)
        
        ttk.Label(search_frame, text="Buscar (Nome/CPF):").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=50).pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        ttk.Button(search_frame, text="Buscar", command=self.update_lista_tab).pack(side=tk.LEFT, padx=5)

        self.search_status_label = ttk.Label(self.lista_frame, text="", foreground="blue")
        self.search_status_label.pack(fill='x')
        # --- FIM: SEÇÃO DE BUSCA ---

        self.tree = ttk.Treeview(self.lista_frame, columns=("Nome", "CPF", "Idade", "Telefone"), show="headings")
        self.tree.heading("Nome", text="Nome"); self.tree.heading("CPF", text="CPF"); self.tree.heading("Idade", text="Idade"); self.tree.heading("Telefone", text="Telefone")
        self.tree.column("Nome", width=250); self.tree.column("CPF", width=150); self.tree.column("Idade", width=80); self.tree.column("Telefone", width=150)
        self.tree.pack(expand=True, fill="both")
        
        button_frame = ttk.Frame(self.lista_frame)
        button_frame.pack(pady=10)
        
        # Botões
        ttk.Button(button_frame, text="Atualizar Lista (Limpar Filtro)", command=lambda: (self.search_var.set(""), self.update_lista_tab())).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Detalhes do Paciente Selecionado", command=self.exibir_detalhes_selecionado).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Imprimir/Salvar em TXT 📄", command=self.exportar_pacientes_para_txt).pack(side=tk.LEFT, padx=15) # --- NOVO BOTÃO
        
        self.update_lista_tab()

    def update_lista_tab(self):
        """Carrega os dados do BD e preenche a tabela da GUI, aplicando o filtro."""
        
        termo = self.search_var.get().strip() if hasattr(self, 'search_var') else ""

        for i in self.tree.get_children():
            self.tree.delete(i)
        
        pacientes_do_bd = self.listar_pacientes_bd(termo) 
        
        for p in pacientes_do_bd:
            self.tree.insert("", "end", values=p)
            
        if not pacientes_do_bd:
             self.tree.insert("", "end", values=("Nenhum paciente encontrado.", "", "", ""))
             
        if termo:
             self.search_status_label.config(text=f"Resultados para: '{termo}'")
        else:
             self.search_status_label.config(text="")


    # --- Aba de Estatísticas ---
    
    def create_estatisticas_tab(self):
        self.stats_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.stats_frame, text=" Estatísticas ")
        self.total_label = ttk.Label(self.stats_frame, text="", font=("Arial", 14))
        self.total_label.pack(pady=10)
        self.media_label = ttk.Label(self.stats_frame, text="", font=("Arial", 14))
        self.media_label.pack(pady=10)
        ttk.Button(self.stats_frame, text="Calcular Estatísticas", command=self.handle_estatisticas).pack(pady=20)
        
    def handle_estatisticas(self):
        """Calcula estatísticas usando o BD."""
        self.cursor.execute("SELECT COUNT(id) FROM pacientes")
        total_pacientes = self.cursor.fetchone()[0]
        
        self.total_label.config(text=f"Total de pacientes cadastrados: {total_pacientes}")
        
        if total_pacientes > 0:
            self.cursor.execute("SELECT AVG(idade) FROM pacientes")
            idade_media = self.cursor.fetchone()[0]
            self.media_label.config(text=f"Idade média dos pacientes: {idade_media:.2f} anos")
        else:
            self.media_label.config(text="Nenhum paciente cadastrado para calcular estatísticas.")


if __name__ == "__main__":
    app = ClinicaApp()
    app.mainloop()