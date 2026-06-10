# -*- coding: utf-8 -*-
import customtkinter as ctk
from app.sheet_manager import SheetManager, GenericRow


class GenericForm(ctk.CTkToplevel):
    """Formulário genérico para editar/criar uma linha de planilha não-estruturada."""

    def __init__(self, master, sheet_manager: SheetManager,
                 row: GenericRow = None, on_saved=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sm = sheet_manager
        self.row = row          # None = nova linha
        self.on_saved = on_saved

        titulo = "Editar Linha" if row else "Nova Linha"
        self.title(titulo)
        self.configure(fg_color="#1E1E2E")
        self.resizable(True, True)
        self.grab_set()

        self._entries: dict[str, ctk.CTkEntry] = {}
        self._build()

        self.update_idletasks()
        w, h = 500, min(600, 80 + len(self.sm.generic_headers) * 60 + 80)
        self.geometry(f"{w}x{h}")
        self.minsize(400, 300)

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Cabeçalho
        ctk.CTkLabel(
            self,
            text="Editar Linha" if self.row else "Nova Linha",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#CDD6F4",
        ).grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        # Área rolável com campos
        scroll = ctk.CTkScrollableFrame(self, fg_color="#1E1E2E", corner_radius=0)
        scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        scroll.grid_columnconfigure(1, weight=1)

        for i, (col_idx, name) in enumerate(self.sm.generic_headers):
            ctk.CTkLabel(
                scroll, text=name,
                text_color="#BAC2DE",
                font=ctk.CTkFont(size=12),
                anchor="e",
            ).grid(row=i, column=0, padx=(16, 8), pady=6, sticky="e")

            entry = ctk.CTkEntry(
                scroll,
                fg_color="#313244", border_color="#45475A",
                text_color="#CDD6F4",
            )
            entry.grid(row=i, column=1, padx=(0, 16), pady=6, sticky="ew")

            if self.row:
                val = self.row.dados.get(name, "")
                entry.insert(0, str(val))

            self._entries[name] = entry

        # Botões
        btn_bar = ctk.CTkFrame(self, fg_color="#181825", corner_radius=0)
        btn_bar.grid(row=2, column=0, sticky="ew", pady=(0, 0))
        btn_bar.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(btn_bar, fg_color="transparent")
        inner.grid(row=0, column=0, padx=16, pady=12, sticky="e")

        ctk.CTkButton(
            inner, text="Cancelar",
            fg_color="#313244", hover_color="#45475A",
            command=self.destroy, width=100,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            inner, text="Salvar",
            fg_color="#1565C0", hover_color="#0D47A1",
            command=self._salvar, width=120,
        ).pack(side="left", padx=4)

    def _salvar(self):
        dados = {name: self._entries[name].get().strip()
                 for name in self._entries}

        if self.row:
            self.row.dados.update(dados)
            self.sm.salvar_generic_row(self.row)
        else:
            self.sm.criar_generic_row(dados)

        self.sm.save()
        self.destroy()
        if self.on_saved:
            self.on_saved()
