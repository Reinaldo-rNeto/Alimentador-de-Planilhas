# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import messagebox
from app.sheet_manager import SheetManager


class SectionForm(ctk.CTkToplevel):
    """Janela para criar uma nova seção na planilha."""

    def __init__(self, master, sheet_manager: SheetManager, on_saved=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sm = sheet_manager
        self.on_saved = on_saved

        self.title("Nova Seção")
        self.geometry("460x260")
        self.resizable(False, False)
        self.configure(fg_color="#1E1E2E")
        self.grab_set()
        self.lift()
        self.focus_force()

        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Criar Nova Seção",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#CDD6F4",
        ).grid(row=0, column=0, padx=24, pady=(24, 4), sticky="w")

        ctk.CTkLabel(
            self,
            text="A seção será inserida após a última seção existente,\n"
                 "com cabeçalho e separadores CRÍTICO / ALTA / MÉDIA / BAIXA.",
            text_color="#6C7086", font=ctk.CTkFont(size=11),
            justify="left",
        ).grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="#313244", corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Nome da seção *",
                     text_color="#BAC2DE", font=ctk.CTkFont(size=12),
                     ).grid(row=0, column=0, padx=(16, 8), pady=16, sticky="e")

        self.entry_nome = ctk.CTkEntry(
            form, placeholder_text="Ex.: Projetos GDA  |  Jun/2026",
            fg_color="#1E1E2E", border_color="#45475A", text_color="#CDD6F4",
        )
        self.entry_nome.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="ew")

        bar = ctk.CTkFrame(self, fg_color="#181825", corner_radius=0)
        bar.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        bar.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            bar, text="Cancelar",
            fg_color="#313244", hover_color="#45475A",
            command=self.destroy, width=110, height=36,
        ).grid(row=0, column=0, padx=(16, 8), pady=12, sticky="e")

        ctk.CTkButton(
            bar, text="Criar Seção",
            fg_color="#1565C0", hover_color="#0D47A1",
            command=self._criar, width=130, height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=1, padx=(0, 16), pady=12)

    def _criar(self):
        nome = self.entry_nome.get().strip()
        if not nome:
            messagebox.showwarning("Campo obrigatório", "Informe o nome da seção.", parent=self)
            return
        try:
            self.sm.criar_secao(nome)
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro ao criar seção", str(e), parent=self)
