# -*- coding: utf-8 -*-
from datetime import date
import customtkinter as ctk
from tkinter import messagebox
from app.sheet_manager import Projeto, SheetManager, CORES_UI


class ObsForm(ctk.CTkToplevel):
    """Janela rápida para adicionar uma observação a um projeto."""

    def __init__(self, master, sheet_manager: SheetManager,
                 projeto: Projeto = None, on_saved=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sm = sheet_manager
        self.projeto = projeto
        self.on_saved = on_saved

        self.title("Adicionar Observação")
        self.geometry("560x420")
        self.resizable(False, False)
        self.configure(fg_color="#1E1E2E")
        self.grab_set()
        self.lift()
        self.focus_force()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build()
        if projeto:
            self._set_projeto(projeto)

    def _build(self):
        # Título
        ctk.CTkLabel(
            self, text="Adicionar Observação",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#CDD6F4",
        ).grid(row=0, column=0, padx=20, pady=(20, 4), sticky="w")

        hoje = date.today().strftime("%d/%m/%Y")
        ctk.CTkLabel(
            self, text=f"Será prefixado com  — {date.today().strftime('%d/%m')}  automaticamente",
            text_color="#6C7086", font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, padx=20, pady=(0, 12), sticky="w")

        # Seletor de projeto
        form = ctk.CTkFrame(self, fg_color="#313244", corner_radius=12)
        form.grid(row=2, column=0, sticky="nsew", padx=16, pady=0)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Projeto", text_color="#BAC2DE",
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=16, pady=(14, 4), sticky="w")

        nomes = [f"#{int(p.num) if p.num else '?'} — {p.nome}" for p in self.sm.projetos]
        self.combo_proj = ctk.CTkComboBox(
            form, values=nomes,
            fg_color="#1E1E2E", border_color="#45475A", text_color="#CDD6F4",
            dropdown_fg_color="#1E1E2E", dropdown_text_color="#CDD6F4",
            button_color="#45475A", state="readonly",
            command=self._on_proj_change,
        )
        self.combo_proj.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")

        # Barra colorida de prioridade
        self.barra_prio = ctk.CTkFrame(form, height=4, corner_radius=0, fg_color="#45475A")
        self.barra_prio.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))

        # Status atual
        self.label_status = ctk.CTkLabel(
            form, text="", text_color="#6C7086", font=ctk.CTkFont(size=11),
        )
        self.label_status.grid(row=3, column=0, padx=16, pady=(0, 8), sticky="w")

        # Texto da observação
        ctk.CTkLabel(form, text="Texto da observação", text_color="#BAC2DE",
                     font=ctk.CTkFont(size=12)).grid(row=4, column=0, padx=16, pady=(4, 4), sticky="w")

        self.txt = ctk.CTkTextbox(
            form, height=100,
            fg_color="#1E1E2E", border_color="#45475A", text_color="#CDD6F4",
            border_width=1, corner_radius=6,
        )
        self.txt.grid(row=5, column=0, padx=16, pady=(0, 16), sticky="ew")

        # Preview
        ctk.CTkLabel(form, text="Preview:", text_color="#6C7086",
                     font=ctk.CTkFont(size=11)).grid(row=6, column=0, padx=16, pady=(0, 4), sticky="w")
        self.label_preview = ctk.CTkLabel(
            form, text=f"- {date.today().strftime('%d/%m')} …",
            text_color="#A6E3A1", font=ctk.CTkFont(size=11, family="Consolas"),
            anchor="w", wraplength=480,
        )
        self.label_preview.grid(row=7, column=0, padx=16, pady=(0, 16), sticky="w")
        self.txt.bind("<KeyRelease>", self._atualizar_preview)

        # Botões
        bar = ctk.CTkFrame(self, fg_color="#181825", corner_radius=0)
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            bar, text="Cancelar",
            fg_color="#313244", hover_color="#45475A",
            command=self.destroy, width=110, height=36,
        ).grid(row=0, column=0, padx=(16, 8), pady=12, sticky="e")

        ctk.CTkButton(
            bar, text="Salvar Observação",
            fg_color="#1565C0", hover_color="#0D47A1",
            command=self._salvar, width=160, height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=1, padx=(0, 16), pady=12)

    def _set_projeto(self, proj: Projeto):
        nome_combo = f"#{int(proj.num) if proj.num else '?'} — {proj.nome}"
        try:
            self.combo_proj.set(nome_combo)
        except Exception:
            pass
        self._atualizar_info_proj(proj)

    def _on_proj_change(self, value: str):
        proj = self._get_proj_by_combo(value)
        if proj:
            self._atualizar_info_proj(proj)

    def _atualizar_info_proj(self, proj: Projeto):
        cor = CORES_UI.get(proj.prio, {}).get("bg", "#45475A")
        self.barra_prio.configure(fg_color=cor)
        self.label_status.configure(
            text=f"Prioridade: {proj.prio}   |   Status: {proj.status}   |   Impeditivo: {proj.impeditivo}"
        )

    def _get_proj_by_combo(self, value: str) -> Projeto:
        for p in self.sm.projetos:
            label = f"#{int(p.num) if p.num else '?'} — {p.nome}"
            if label == value:
                return p
        return None

    def _atualizar_preview(self, event=None):
        texto = self.txt.get("1.0", "end").strip()
        preview = f"- {date.today().strftime('%d/%m')} {texto}" if texto else f"- {date.today().strftime('%d/%m')} …"
        self.label_preview.configure(text=preview[:100] + ("…" if len(preview) > 100 else ""))

    def _salvar(self):
        combo_val = self.combo_proj.get()
        proj = self._get_proj_by_combo(combo_val) or self.projeto
        if not proj:
            messagebox.showwarning("Selecione o projeto", "Escolha um projeto antes de salvar.", parent=self)
            return

        texto = self.txt.get("1.0", "end").strip()
        if not texto:
            messagebox.showwarning("Texto vazio", "Escreva o texto da observação.", parent=self)
            return

        self.sm.adicionar_observacao(proj, texto)
        self.sm.save()
        if self.on_saved:
            self.on_saved()
        self.destroy()
