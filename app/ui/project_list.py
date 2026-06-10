# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from app.sheet_manager import SheetManager, Projeto, GenericRow, CORES_UI, PRIORIDADES, STATUS_OPCOES


class ProjectListScreen(ctk.CTkFrame):
    """Tela principal: lista de todos os projetos com filtros e ações."""

    COLS = [
        ("prio",       "Prio",          80),
        ("num",        "#",             40),
        ("nome",       "Projeto",       300),
        ("demandante", "Demandante",    110),
        ("responsavel","Responsável",   110),
        ("status",     "Status",        130),
        ("impeditivo", "Impeditivo",     90),
        ("dt_estimada","DT Estimada",   100),
        ("tipo",       "Tipo",          110),
        ("secao",      "Seção",         180),
    ]

    def __init__(self, master, sheet_manager: SheetManager,
                 on_edit, on_new, on_obs, on_sync,
                 on_voltar, on_nova_secao=None,
                 drive_manager=None, on_desconectar_drive=None,
                 # legado — mantido para compatibilidade
                 on_trocar_arquivo=None,
                 **kwargs):
        super().__init__(master, **kwargs)
        self.sm = sheet_manager
        self.drive_manager = drive_manager
        self.on_edit = on_edit
        self.on_new = on_new
        self.on_obs = on_obs
        self.on_sync = on_sync
        self.on_voltar = on_voltar
        self.on_trocar_arquivo = on_voltar  # mesmo que voltar
        self.on_nova_secao = on_nova_secao
        self.on_desconectar_drive = on_desconectar_drive
        self._all_projects: list[Projeto] = []
        self._filtered: list[Projeto] = []
        self._selected_proj: Projeto = None
        # Modo genérico
        self._all_generic: list[GenericRow] = []
        self._filtered_generic: list[GenericRow] = []
        self._selected_generic: GenericRow = None

        self.configure(fg_color="#1E1E2E")
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_filters()
        self._build_treeview()
        self._build_bottombar()
        self.refresh()

    # ------------------------------------------------------------------ #
    #  Topbar                                                              #
    # ------------------------------------------------------------------ #

    def _build_topbar(self):
        top = ctk.CTkFrame(self, fg_color="#181825", corner_radius=0)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        # Botão Voltar
        ctk.CTkButton(
            top, text="← Voltar",
            fg_color="transparent", hover_color="#313244",
            text_color="#CDD6F4", border_width=1, border_color="#45475A",
            command=self.on_voltar, width=90, height=30,
        ).grid(row=0, column=0, padx=(12, 4), pady=12, sticky="w")

        nome = self.sm.filepath.replace("\\", "/").split("/")[-1]
        self.label_arquivo = ctk.CTkLabel(
            top, text=f"📋  {nome}  |  {self.sm.sheet_name}",
            font=ctk.CTkFont(size=12), text_color="#6C7086",
        )
        self.label_arquivo.grid(row=0, column=1, padx=8, pady=12)

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=12, pady=8)

        ctk.CTkButton(
            btn_frame, text="☁ Sincronizar",
            fg_color="#1565C0", hover_color="#0D47A1",
            command=self.on_sync, width=110, height=30,
        ).pack(side="left", padx=3)

        # Indicador / botão Drive
        if self.drive_manager and self.drive_manager.esta_autenticado():
            try:
                usuario = self.drive_manager.get_usuario()
            except Exception:
                usuario = "conectado"
            ctk.CTkButton(
                btn_frame,
                text=f"✓ Drive: {usuario[:20]}",
                fg_color="#1B5E20", hover_color="#2E7D32",
                width=180, height=30,
                command=self._confirmar_desconectar,
            ).pack(side="left", padx=3)
        else:
            ctk.CTkButton(
                btn_frame, text="Drive desconectado",
                fg_color="#45475A", hover_color="#45475A",
                text_color="#6C7086", width=160, height=30,
                state="disabled",
            ).pack(side="left", padx=3)

    def _confirmar_desconectar(self):
        from tkinter import messagebox
        if messagebox.askyesno("Desconectar Drive",
                               "Deseja encerrar a conexão com o Google Drive?\n"
                               "Você voltará para a tela inicial."):
            if self.on_desconectar_drive:
                self.on_desconectar_drive()

    # ------------------------------------------------------------------ #
    #  Filtros                                                             #
    # ------------------------------------------------------------------ #

    def _build_filters(self):
        filt = ctk.CTkFrame(self, fg_color="#313244", corner_radius=0)
        filt.grid(row=1, column=0, sticky="ew")

        inner = ctk.CTkFrame(filt, fg_color="transparent")
        inner.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        def lbl(text):
            return ctk.CTkLabel(inner, text=text, text_color="#CDD6F4",
                                font=ctk.CTkFont(size=12))

        def combo(values, width=130):
            return ctk.CTkComboBox(
                inner, values=values, width=width,
                fg_color="#1E1E2E", border_color="#45475A",
                text_color="#CDD6F4", dropdown_fg_color="#313244",
                dropdown_text_color="#CDD6F4", button_color="#45475A",
                state="readonly", command=lambda v: self._aplicar_filtros(),
            )

        # Busca
        lbl("Buscar:").pack(side="left", padx=(4, 2))
        self.entry_busca = ctk.CTkEntry(
            inner, placeholder_text="Buscar…", width=200,
            fg_color="#1E1E2E", border_color="#45475A", text_color="#CDD6F4",
        )
        self.entry_busca.pack(side="left", padx=2)
        self.entry_busca.bind("<KeyRelease>", lambda e: self._aplicar_filtros())

        # Filtros só para modo estruturado
        if self.sm.mode == "structured":
            lbl("  Prio:").pack(side="left", padx=(8, 2))
            self.combo_prio = combo(["Todas"] + PRIORIDADES, 120)
            self.combo_prio.set("Todas")
            self.combo_prio.pack(side="left", padx=2)

            lbl("  Status:").pack(side="left", padx=(8, 2))
            self.combo_status = combo(["Todos"] + STATUS_OPCOES, 150)
            self.combo_status.set("Todos")
            self.combo_status.pack(side="left", padx=2)

            secoes = ["Todas as seções"] + [s.titulo for s in self.sm.secoes]
            lbl("  Seção:").pack(side="left", padx=(8, 2))
            self.combo_secao = combo(secoes, 200)
            self.combo_secao.set(secoes[0])
            self.combo_secao.pack(side="left", padx=2)
        else:
            self.combo_prio = None
            self.combo_status = None
            self.combo_secao = None

        # Badge modo genérico
        if self.sm.mode == "generic":
            ctk.CTkLabel(
                inner, text="  ⚡ Modo Genérico",
                text_color="#F9E2AF", font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=(12, 2))

    # ------------------------------------------------------------------ #
    #  Treeview                                                            #
    # ------------------------------------------------------------------ #

    def _build_treeview(self):
        frame = tk.Frame(self, bg="#1E1E2E")
        frame.grid(row=2, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#2A2A3E", foreground="#CDD6F4",
                        rowheight=30, fieldbackground="#2A2A3E",
                        borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background="#313244", foreground="#CDD6F4",
                        font=("Segoe UI", 10, "bold"), borderwidth=0,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", "#3D59A1")],
                  foreground=[("selected", "#FFFFFF")],
                  relief=[("selected", "flat")])

        if self.sm.mode == "generic":
            self._build_treeview_generic(frame)
        else:
            self._build_treeview_structured(frame)

        self._sort_col = None
        self._sort_rev = False

    def _build_treeview_structured(self, frame):
        col_ids = [c[0] for c in self.COLS]
        self.tree = ttk.Treeview(frame, columns=col_ids,
                                 show="headings", selectmode="browse")

        for col_id, label, width in self.COLS:
            self.tree.heading(col_id, text=label,
                              command=lambda c=col_id: self._sort_by(c))
            stretch = col_id == "nome"
            self.tree.column(col_id, width=width, minwidth=30, stretch=stretch)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        PRIO_BG = {
            "Crítica": ("#FFEBEE", "#B71C1C"),
            "Alta":    ("#FBE9E7", "#E65100"),
            "Média":   ("#E3F2FD", "#1565C0"),
            "Baixa":   ("#ECEFF1", "#37474F"),
        }
        for prio, (bg_row, _) in PRIO_BG.items():
            self.tree.tag_configure(f"prio_{prio}", background=bg_row, foreground="#1A1A2E")
        self.tree.tag_configure("sem_prio", background="#2A2A3E", foreground="#CDD6F4")

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_treeview_generic(self, frame):
        # Colunas detectadas da planilha
        hdrs = self.sm.generic_headers  # [(col_idx, nome), ...]
        col_ids = [name for _, name in hdrs]

        self.tree = ttk.Treeview(frame, columns=col_ids,
                                 show="headings", selectmode="browse")

        first_col = col_ids[0] if col_ids else None
        for name in col_ids:
            self.tree.heading(name, text=name,
                              command=lambda c=name: self._sort_by_generic(c))
            # Primeira coluna mais larga; demais usam 120
            stretch = name == first_col
            self.tree.column(name, width=200 if stretch else 120,
                             minwidth=60, stretch=stretch)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.tag_configure("row_alt", background="#313244", foreground="#CDD6F4")
        self.tree.tag_configure("row_std", background="#2A2A3E", foreground="#CDD6F4")

        self.tree.bind("<Double-1>", self._on_double_click_generic)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_generic)

    # ------------------------------------------------------------------ #
    #  Barra inferior                                                      #
    # ------------------------------------------------------------------ #

    def _build_bottombar(self):
        bar = ctk.CTkFrame(self, fg_color="#181825", corner_radius=0)
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)

        self.label_total = ctk.CTkLabel(
            bar, text="0 registros", text_color="#6C7086",
            font=ctk.CTkFont(size=12),
        )
        self.label_total.grid(row=0, column=0, padx=16, pady=10, sticky="w")

        btn_frame = ctk.CTkFrame(bar, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=16, pady=8)

        if self.sm.mode == "generic":
            btns = [
                ("+ Nova Linha",  self.on_new,              "#1565C0", "#0D47A1", 130),
                ("✎ Editar",      self._editar_selecionado,  "#313244", "#45475A", 100),
            ]
        else:
            btns = [
                ("+ Novo Projeto",  self.on_new,              "#1565C0", "#0D47A1", 140),
                ("✎ Editar",        self._editar_selecionado,  "#313244", "#45475A", 100),
                ("📝 Observação",   self._obs_selecionado,     "#313244", "#45475A", 120),
                ("＋ Nova Seção",   self._nova_secao,          "#313244", "#45475A", 120),
            ]

        for text, cmd, fg, hover, w in btns:
            ctk.CTkButton(
                btn_frame, text=text, command=cmd,
                fg_color=fg, hover_color=hover,
                height=36, width=w,
                font=ctk.CTkFont(size=13, weight="bold") if "Novo" in text or "Nova" in text else None,
                border_width=0 if "Novo" in text or "Nova" in text else 1,
                border_color="#6C7086",
            ).pack(side="left", padx=4)

    # ------------------------------------------------------------------ #
    #  Dados                                                               #
    # ------------------------------------------------------------------ #

    def refresh(self):
        try:
            if self.sm.mode == "generic":
                self._all_generic = list(self.sm.generic_rows)
            else:
                self._all_projects = list(self.sm.projetos)
                if self.combo_secao:
                    secoes = ["Todas as seções"] + [s.titulo for s in self.sm.secoes]
                    self.combo_secao.configure(values=secoes)
            self._aplicar_filtros()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Erro ao carregar dados",
                                 f"Não foi possível carregar a planilha:\n\n{e}")

    def _aplicar_filtros(self):
        busca = self.entry_busca.get().lower().strip()

        if self.sm.mode == "generic":
            result = []
            for gr in self._all_generic:
                if busca:
                    row_text = " ".join(str(v).lower() for v in gr.dados.values())
                    if busca not in row_text:
                        continue
                result.append(gr)
            self._filtered_generic = result
            self.label_total.configure(text=f"{len(result)} registro(s)")
            self._render_tree_generic()
            return

        prio_f   = self.combo_prio.get() if self.combo_prio else "Todas"
        status_f = self.combo_status.get() if self.combo_status else "Todos"
        secao_f  = self.combo_secao.get() if self.combo_secao else ""

        result = []
        for p in self._all_projects:
            if busca and busca not in p.nome.lower() and busca not in p.demandante.lower():
                continue
            if prio_f != "Todas" and p.prio != prio_f:
                continue
            if status_f != "Todos" and p.status.strip() != status_f.strip():
                continue
            if secao_f not in ("Todas as seções", "") and p.secao != secao_f:
                continue
            result.append(p)

        self._filtered = result
        self.label_total.configure(text=f"{len(result)} projeto(s)")
        self._render_tree()

    # Prefixos visuais por status (texto, sem mexer na cor de fundo)
    _STATUS_ICON = {
        "conclu":    "✓ ",
        "andamento": "▶ ",
        "iniciar":   "○ ",
        "análise":   "⧖ ",
        "analise":   "⧖ ",
        "suspenso":  "⏸ ",
        "impeditivo":"⚠ ",
        "homologaç": "🔍 ",
        "discovery": "🔎 ",
    }

    def _render_tree(self):
        self.tree.delete(*self.tree.get_children())

        from app.sheet_manager import PRIORIDADES
        for proj in self._filtered:
            num_str = str(int(proj.num)) if proj.num is not None else "-"
            st_raw  = proj.status.strip()
            st_low  = st_raw.lower()

            # Prefixo de status no texto da coluna Status
            icone = ""
            for chave, ic in self._STATUS_ICON.items():
                if chave in st_low:
                    icone = ic
                    break
            st_display = icone + st_raw

            # Indicador de impeditivo
            imp_display = ("⚠ " if proj.impeditivo == "SIM" else "") + proj.impeditivo

            valores = (
                proj.prio,
                num_str,
                proj.nome,
                proj.demandante,
                proj.responsavel,
                st_display,
                imp_display,
                proj.dt_estimada,
                proj.tipo,
                proj.secao[:30] + ("…" if len(proj.secao) > 30 else ""),
            )

            # Tag: apenas prioridade define a cor de fundo
            tag = f"prio_{proj.prio}" if proj.prio in PRIORIDADES else "sem_prio"

            self.tree.insert("", "end", values=valores,
                             tags=(tag,), iid=str(proj.linha))

    def _render_tree_generic(self):
        self.tree.delete(*self.tree.get_children())
        col_names = [name for _, name in self.sm.generic_headers]
        for i, gr in enumerate(self._filtered_generic):
            valores = tuple(gr.dados.get(n, "") for n in col_names)
            tag = "row_alt" if i % 2 else "row_std"
            self.tree.insert("", "end", values=valores, tags=(tag,), iid=str(gr.linha))

    # ------------------------------------------------------------------ #
    #  Interação                                                           #
    # ------------------------------------------------------------------ #

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        linha = int(sel[0])
        for p in self._filtered:
            if p.linha == linha:
                self._selected_proj = p
                return

    def _on_select_generic(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        linha = int(sel[0])
        for gr in self._filtered_generic:
            if gr.linha == linha:
                self._selected_generic = gr
                return

    def _on_double_click(self, event=None):
        self._on_select()
        if self._selected_proj:
            self.on_edit(self._selected_proj)

    def _on_double_click_generic(self, event=None):
        self._on_select_generic()
        if self._selected_generic:
            self.on_edit(self._selected_generic)

    def _editar_selecionado(self):
        if self.sm.mode == "generic":
            self._on_select_generic()
            if self._selected_generic:
                self.on_edit(self._selected_generic)
        else:
            self._on_select()
            if self._selected_proj:
                self.on_edit(self._selected_proj)

    def _obs_selecionado(self):
        self._on_select()
        self.on_obs(self._selected_proj)

    def _nova_secao(self):
        if self.on_nova_secao:
            self.on_nova_secao()

    # ------------------------------------------------------------------ #
    #  Ordenação por coluna                                                #
    # ------------------------------------------------------------------ #

    def _sort_by(self, col_id: str):
        if self._sort_col == col_id:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col_id
            self._sort_rev = False

        def key(p: Projeto):
            v = getattr(p, col_id, "") or ""
            if col_id == "num":
                return p.num or 9999
            return str(v).lower()

        self._filtered.sort(key=key, reverse=self._sort_rev)
        self._render_tree()

    def _sort_by_generic(self, col_name: str):
        if self._sort_col == col_name:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col_name
            self._sort_rev = False

        self._filtered_generic.sort(
            key=lambda gr: str(gr.dados.get(col_name, "")).lower(),
            reverse=self._sort_rev,
        )
        self._render_tree_generic()
