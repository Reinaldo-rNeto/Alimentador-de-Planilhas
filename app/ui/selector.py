# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from pathlib import Path
import threading


class SelectorScreen(ctk.CTkFrame):
    """Tela inicial: abrir arquivo local ou conectar ao Google Drive."""

    def __init__(self, master, on_file_selected, drive_manager=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_file_selected = on_file_selected
        self.drive_manager = drive_manager
        self._drive_files = []
        self._selected_drive_file = None
        self._selected_sheet_name = None
        self._sheet_manager = None

        self._build()

    def _build(self):
        self.configure(fg_color="#1E1E2E")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Scroll externo — `c` é o container pai dos widgets, `self` permanece SelectorScreen
        c = ctk.CTkScrollableFrame(self, fg_color="#1E1E2E", corner_radius=0)
        c.grid(row=0, column=0, sticky="nsew")
        c.grid_columnconfigure(0, weight=1)

        # Título
        ctk.CTkLabel(
            c, text="Alimentador de Planilha",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#CDD6F4",
        ).grid(row=0, column=0, pady=(40, 4))

        ctk.CTkLabel(
            c, text="GDA / ATI-PE",
            font=ctk.CTkFont(size=13),
            text_color="#6C7086",
        ).grid(row=1, column=0, pady=(0, 30))

        # Separador visual
        ctk.CTkFrame(c, height=2, fg_color="#313244").grid(
            row=2, column=0, sticky="ew", padx=60, pady=(0, 30)
        )

        # ── Arquivo local ──────────────────────────────────────────
        local_frame = ctk.CTkFrame(c, fg_color="#313244", corner_radius=12)
        local_frame.grid(row=3, column=0, padx=60, pady=8, sticky="ew")
        local_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            local_frame, text="📂  Arquivo local",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#CDD6F4",
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 8), sticky="w")

        self.entry_local = ctk.CTkEntry(
            local_frame, placeholder_text="Selecione um arquivo .xlsx…",
            fg_color="#1E1E2E", border_color="#45475A", text_color="#CDD6F4",
        )
        self.entry_local.grid(row=1, column=0, padx=(20, 8), pady=(0, 16), sticky="ew")

        ctk.CTkButton(
            local_frame, text="Procurar",
            fg_color="#1565C0", hover_color="#0D47A1",
            command=self._browse_local, width=100,
        ).grid(row=1, column=1, padx=(0, 20), pady=(0, 16))

        # ── Google Drive ───────────────────────────────────────────
        drive_frame = ctk.CTkFrame(c, fg_color="#313244", corner_radius=12)
        drive_frame.grid(row=4, column=0, padx=60, pady=8, sticky="ew")
        drive_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            drive_frame, text="☁️  Google Drive",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#CDD6F4",
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 8), sticky="w")

        self.btn_connect = ctk.CTkButton(
            drive_frame, text="Conectar ao Drive",
            fg_color="#B71C1C" if not self._is_authenticated() else "#1B5E20",
            hover_color="#7F0000" if not self._is_authenticated() else "#1B5E20",
            command=self._connect_drive,
        )
        self.btn_connect.grid(row=1, column=0, padx=20, pady=(0, 12), sticky="ew")

        self.label_user = ctk.CTkLabel(
            drive_frame, text="", text_color="#A6E3A1",
            font=ctk.CTkFont(size=12),
        )
        self.label_user.grid(row=2, column=0, padx=20, pady=(0, 4))

        self.drive_search = ctk.CTkEntry(
            drive_frame, placeholder_text="Buscar planilha no Drive…",
            fg_color="#1E1E2E", border_color="#45475A", text_color="#CDD6F4",
        )
        self.drive_search.grid(row=3, column=0, padx=20, pady=(4, 8), sticky="ew")
        self.drive_search.bind("<Return>", lambda e: self._search_drive())

        ctk.CTkButton(
            drive_frame, text="Buscar",
            fg_color="#313244", hover_color="#45475A", border_width=1, border_color="#6C7086",
            command=self._search_drive, width=80,
        ).grid(row=3, column=1, padx=(0, 20), pady=(4, 8))

        self.drive_list = ctk.CTkScrollableFrame(
            drive_frame, height=120, fg_color="#1E1E2E",
        )
        self.drive_list.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 16), sticky="ew")
        self.drive_list.grid_columnconfigure(0, weight=1)

        # ── Seleção de aba ─────────────────────────────────────────
        aba_frame = ctk.CTkFrame(c, fg_color="#313244", corner_radius=12)
        aba_frame.grid(row=5, column=0, padx=60, pady=8, sticky="ew")
        aba_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            aba_frame, text="📋  Selecionar Aba",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#CDD6F4",
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 8), sticky="w")

        self.combo_aba = ctk.CTkComboBox(
            aba_frame, values=["— nenhum arquivo carregado —"],
            fg_color="#1E1E2E", border_color="#45475A", text_color="#CDD6F4",
            dropdown_fg_color="#313244", dropdown_text_color="#CDD6F4",
            button_color="#1565C0", button_hover_color="#0D47A1",
            state="disabled",
        )
        self.combo_aba.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 16), sticky="ew")

        # ── Botão abrir ────────────────────────────────────────────
        self.btn_abrir = ctk.CTkButton(
            c, text="Abrir Planilha  →",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#1565C0", hover_color="#0D47A1",
            height=44, corner_radius=10,
            command=self._abrir,
            state="disabled",
        )
        self.btn_abrir.grid(row=6, column=0, padx=60, pady=(16, 40), sticky="ew")

        # Restaurar último arquivo salvo
        self._restaurar_ultimo()

    # ------------------------------------------------------------------ #

    def _is_authenticated(self) -> bool:
        from pathlib import Path
        token = Path.home() / ".alimentador_planilha" / "token.json"
        return token.exists()

    def _browse_local(self):
        path = filedialog.askopenfilename(
            title="Selecionar planilha",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Todos", "*.*")],
        )
        if path:
            self.entry_local.delete(0, "end")
            self.entry_local.insert(0, path)
            self._selected_drive_file = None
            self._carregar_abas_local(path)

    def _carregar_abas_local(self, path: str):
        try:
            from app.sheet_manager import SheetManager
            sm = SheetManager(path)
            abas = sm.get_sheet_names()
            self._sheet_manager = sm
            self.combo_aba.configure(values=abas, state="readonly")
            self.combo_aba.set(abas[0])
            self.btn_abrir.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível ler o arquivo:\n{e}")

    def _connect_drive(self):
        if not self.drive_manager:
            # Tentar localizar credentials.json manualmente
            path = filedialog.askopenfilename(
                title="Localizar credentials.json",
                filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
            )
            if not path:
                messagebox.showinfo(
                    "credentials.json não encontrado",
                    "Coloque o arquivo credentials.json na mesma pasta do AlimentadorPlanilha.exe\n"
                    "e abra o programa novamente.\n\n"
                    "Se não tiver o arquivo, peça ao administrador do sistema.",
                )
                return
            from app.drive_manager import DriveManager
            self.drive_manager = DriveManager(path)
            # Salvar caminho para uso futuro
            config = self._load_config()
            config["credentials_path"] = path
            self._save_config(config)

        if self._is_authenticated():
            if messagebox.askyesno("Desconectar", "Deseja sair da conta Google?"):
                self.drive_manager.desconectar()
                self.btn_connect.configure(text="Conectar ao Drive", fg_color="#B71C1C")
                self.label_user.configure(text="")
            return

        self.btn_connect.configure(
            text="🌐 Abrindo navegador… (aguarde até 2 min)",
            state="disabled", fg_color="#45475A",
        )
        self._auth_countdown = 120
        self._tick_auth()

        def _auth():
            try:
                self.drive_manager.autenticar()
                usuario = self.drive_manager.get_usuario()
                self.after(0, lambda: self._on_auth_ok(usuario))
            except Exception as e:
                self.after(0, lambda: self._on_auth_err(str(e)))

        threading.Thread(target=_auth, daemon=True).start()

    def _tick_auth(self):
        """Atualiza o contador regressivo no botão enquanto aguarda o OAuth."""
        if not hasattr(self, "_auth_countdown") or self._auth_countdown is None:
            return
        if self._auth_countdown <= 0:
            return
        try:
            if self.btn_connect.cget("state") == "disabled":
                self.btn_connect.configure(
                    text=f"🌐 Aguardando login… ({self._auth_countdown}s)"
                )
                self._auth_countdown -= 1
                self.after(1000, self._tick_auth)
        except Exception:
            pass

    def _on_auth_ok(self, usuario: str):
        self._auth_countdown = None
        self.btn_connect.configure(
            text="✓ Conectado — Sair", fg_color="#1B5E20", state="normal"
        )
        self.label_user.configure(text=f"Conta: {usuario}")
        self._search_drive()

    def _on_auth_err(self, msg: str):
        self._auth_countdown = None
        self.btn_connect.configure(text="Conectar ao Drive", state="normal", fg_color="#B71C1C")
        messagebox.showerror("Erro de autenticação", msg)

    def _search_drive(self):
        if not self.drive_manager or not self.drive_manager.esta_autenticado():
            return
        query = self.drive_search.get().strip()

        def _fetch():
            files = self.drive_manager.listar_planilhas(query)
            self.after(0, lambda: self._mostrar_drive_files(files))

        threading.Thread(target=_fetch, daemon=True).start()

    def _mostrar_drive_files(self, files: list):
        for w in self.drive_list.winfo_children():
            w.destroy()
        self._drive_files = files
        if not files:
            ctk.CTkLabel(
                self.drive_list, text="Nenhuma planilha encontrada.",
                text_color="#6C7086",
            ).grid(row=0, column=0, padx=8, pady=4)
            return
        for i, f in enumerate(files):
            icon = "📊" if "spreadsheet" in f.get("mimeType", "") else "📗"
            btn = ctk.CTkButton(
                self.drive_list,
                text=f"{icon}  {f['name']}",
                fg_color="transparent", hover_color="#313244",
                text_color="#CDD6F4", anchor="w",
                command=lambda fid=f["id"], fn=f["name"], fm=f["mimeType"]: self._selecionar_drive(fid, fn, fm),
            )
            btn.grid(row=i, column=0, sticky="ew", padx=4, pady=2)

    def _selecionar_drive(self, file_id: str, name: str, mime: str):
        self._selected_drive_file = {"id": file_id, "name": name, "mimeType": mime}
        self.entry_local.delete(0, "end")

        def _download():
            try:
                tmp_path = self.drive_manager.download_para_temp(file_id, mime)
                self.after(0, lambda: self._carregar_abas_drive(tmp_path, name))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro", str(e)))

        threading.Thread(target=_download, daemon=True).start()

    def _carregar_abas_drive(self, tmp_path: str, name: str):
        try:
            from app.sheet_manager import SheetManager
            sm = SheetManager(tmp_path)
            abas = sm.get_sheet_names()
            self._sheet_manager = sm
            self.combo_aba.configure(values=abas, state="readonly")
            self.combo_aba.set(abas[0])
            self.btn_abrir.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _abrir(self):
        aba = self.combo_aba.get()
        if not self._sheet_manager:
            return
        self._sheet_manager.load(aba)
        self._salvar_ultimo(self._sheet_manager.filepath, aba)
        self.on_file_selected(self._sheet_manager, self._selected_drive_file)

    def _restaurar_ultimo(self):
        config = self._load_config()
        ultimo = config.get("ultimo_arquivo", "")
        if ultimo and Path(ultimo).exists():
            self.entry_local.insert(0, ultimo)
            self._carregar_abas_local(ultimo)
            ultima_aba = config.get("ultima_aba", "")
            if ultima_aba:
                try:
                    self.combo_aba.set(ultima_aba)
                except Exception:
                    pass

    def _salvar_ultimo(self, path: str, aba: str):
        config = self._load_config()
        config["ultimo_arquivo"] = path
        config["ultima_aba"] = aba
        self._save_config(config)

    def _load_config(self) -> dict:
        import json
        cfg_path = Path.home() / ".alimentador_planilha" / "config.json"
        if cfg_path.exists():
            try:
                return json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_config(self, data: dict):
        import json
        cfg_path = Path.home() / ".alimentador_planilha" / "config.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
