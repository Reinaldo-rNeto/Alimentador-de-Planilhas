# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import messagebox
from app.sheet_manager import (
    Projeto, SheetManager, PRIORIDADES, STATUS_OPCOES,
    IMPEDITIVO_OPCOES, TIPO_OPCOES, NATUREZA_OPCOES, CORES_UI,
)


class ProjectForm(ctk.CTkToplevel):
    """Janela modal para criar ou editar um projeto."""

    def __init__(self, master, sheet_manager: SheetManager,
                 projeto: Projeto = None, on_saved=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sm = sheet_manager
        self.projeto = projeto  # None = novo
        self.on_saved = on_saved
        self._is_new = projeto is None

        self.title("Novo Projeto" if self._is_new else f"Editar — {projeto.nome[:40]}")
        self.geometry("720x720")
        self.resizable(True, True)
        self.configure(fg_color="#1E1E2E")
        self.grab_set()   # modal
        self.lift()
        self.focus_force()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build()
        if not self._is_new:
            self._preencher(projeto)

    # ------------------------------------------------------------------ #
    #  Build                                                               #
    # ------------------------------------------------------------------ #

    def _build(self):
        # Barra colorida de prioridade (muda ao alterar o combo)
        self.barra_prio = ctk.CTkFrame(self, height=8, corner_radius=0)
        self.barra_prio.grid(row=0, column=0, sticky="ew")

        # Scroll frame principal
        scroll = ctk.CTkScrollableFrame(self, fg_color="#1E1E2E")
        scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        scroll.grid_columnconfigure((0, 1), weight=1)

        # ── Seção e Prioridade ─────────────────────────────────────
        secoes = [s.titulo for s in self.sm.secoes]
        self._add_label(scroll, "Seção *", 0, 0)
        self.combo_secao = self._combo(scroll, secoes, 0, 1)
        if secoes:
            self.combo_secao.set(secoes[0])

        self._add_label(scroll, "Prioridade *", 1, 0)
        self.combo_prio = self._combo(scroll, PRIORIDADES, 1, 1)
        self.combo_prio.set("Alta")
        self.combo_prio.configure(command=self._atualizar_cor_prio)
        self._atualizar_cor_prio("Alta")

        # ── Nome do projeto ────────────────────────────────────────
        self._add_label(scroll, "Nome do Projeto *", 2, 0)
        self.entry_nome = self._entry(scroll, 2, 1, colspan=1)
        self.entry_nome.configure(placeholder_text="Ex.: Painel de Gestão SEFAZ")

        # ── Natureza / Tipo ────────────────────────────────────────
        self._add_label(scroll, "Natureza", 3, 0)
        self.combo_natureza = self._combo(scroll, NATUREZA_OPCOES, 3, 1)

        self._add_label(scroll, "Tipo", 4, 0)
        self.combo_tipo = self._combo(scroll, TIPO_OPCOES, 4, 1)

        # ── Demandante ─────────────────────────────────────────────
        self._add_label(scroll, "Demandante", 5, 0)
        self.entry_demandante = self._entry(scroll, 5, 1)
        self.entry_demandante.configure(placeholder_text="Ex.: SEFAZ, GDA, PGE…")

        # ── Responsável / Acompanhamento ───────────────────────────
        self._add_label(scroll, "Responsável", 6, 0)
        self.entry_resp = self._entry(scroll, 6, 1)

        self._add_label(scroll, "Acompanhamento", 7, 0)
        self.entry_acomp = self._entry(scroll, 7, 1)

        # ── Status / Impeditivo ────────────────────────────────────
        self._add_label(scroll, "Status", 8, 0)
        self.combo_status = self._combo(scroll, STATUS_OPCOES, 8, 1)
        self.combo_status.set("A Iniciar")

        self._add_label(scroll, "Impeditivo", 9, 0)
        self.combo_imp = self._combo(scroll, IMPEDITIVO_OPCOES, 9, 1)
        self.combo_imp.set("Normal")

        # ── Datas ──────────────────────────────────────────────────
        self._add_label(scroll, "DT Início", 10, 0)
        self.entry_dt_inicio = self._entry(scroll, 10, 1)
        self.entry_dt_inicio.configure(placeholder_text="DD/MM/AAAA ou -")

        self._add_label(scroll, "DT Estimada", 11, 0)
        self.entry_dt_est = self._entry(scroll, 11, 1)
        self.entry_dt_est.configure(placeholder_text="DD/MM/AAAA, A definir ou -")

        self._add_label(scroll, "DT Entrega", 12, 0)
        self.entry_dt_ent = self._entry(scroll, 12, 1)
        self.entry_dt_ent.configure(placeholder_text="DD/MM/AAAA ou -")

        # ── Observação ─────────────────────────────────────────────
        self._add_label(scroll, "Observação / Log", 13, 0)
        self.txt_obs = ctk.CTkTextbox(
            scroll, height=120, fg_color="#181825", border_color="#45475A",
            text_color="#CDD6F4", border_width=1, corner_radius=6,
        )
        self.txt_obs.grid(row=13, column=1, padx=(4, 16), pady=6, sticky="ew")

        # ── Notas extras ───────────────────────────────────────────
        self._add_label(scroll, "Notas", 14, 0)
        self.entry_notas = self._entry(scroll, 14, 1)

        # ── Botões ─────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="#181825", corner_radius=0)
        btn_row.grid(row=2, column=0, sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_row, text="Cancelar",
            fg_color="#313244", hover_color="#45475A",
            command=self.destroy, width=120, height=38,
        ).grid(row=0, column=0, padx=(16, 8), pady=12, sticky="e")

        self.btn_salvar = ctk.CTkButton(
            btn_row, text="Salvar Projeto",
            fg_color="#1565C0", hover_color="#0D47A1",
            command=self._salvar, width=150, height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_salvar.grid(row=0, column=1, padx=(0, 16), pady=12)

    # ------------------------------------------------------------------ #
    #  Helpers de widget                                                   #
    # ------------------------------------------------------------------ #

    def _add_label(self, parent, text: str, row: int, col: int):
        ctk.CTkLabel(
            parent, text=text, text_color="#BAC2DE",
            font=ctk.CTkFont(size=12), anchor="e",
        ).grid(row=row, column=col, padx=(16, 8), pady=6, sticky="e")

    def _entry(self, parent, row: int, col: int, colspan: int = 1) -> ctk.CTkEntry:
        e = ctk.CTkEntry(
            parent, fg_color="#181825", border_color="#45475A", text_color="#CDD6F4",
            corner_radius=6,
        )
        e.grid(row=row, column=col, columnspan=colspan, padx=(4, 16), pady=6, sticky="ew")
        return e

    def _combo(self, parent, values: list, row: int, col: int) -> ctk.CTkComboBox:
        c = ctk.CTkComboBox(
            parent, values=values,
            fg_color="#181825", border_color="#45475A", text_color="#CDD6F4",
            dropdown_fg_color="#313244", dropdown_text_color="#CDD6F4",
            button_color="#45475A", button_hover_color="#6C7086",
            state="readonly",
        )
        c.grid(row=row, column=col, padx=(4, 16), pady=6, sticky="ew")
        return c

    # ------------------------------------------------------------------ #
    #  Cor dinâmica por prioridade                                         #
    # ------------------------------------------------------------------ #

    def _atualizar_cor_prio(self, prio: str = None):
        if not prio:
            prio = self.combo_prio.get()
        cor = CORES_UI.get(prio, {}).get("bg", "#313244")
        self.barra_prio.configure(fg_color=cor)

    # ------------------------------------------------------------------ #
    #  Preencher (modo edição)                                             #
    # ------------------------------------------------------------------ #

    def _preencher(self, p: Projeto):
        self.combo_secao.set(p.secao)
        self.combo_prio.set(p.prio)
        self._atualizar_cor_prio(p.prio)
        self.entry_nome.insert(0, p.nome)
        self.combo_natureza.set(p.natureza or NATUREZA_OPCOES[0])
        self.combo_tipo.set(p.tipo or TIPO_OPCOES[0])
        self.entry_demandante.insert(0, p.demandante)
        self.entry_resp.insert(0, p.responsavel)
        self.entry_acomp.insert(0, p.acompanhamento)
        self.combo_status.set(p.status or STATUS_OPCOES[0])
        self.combo_imp.set(p.impeditivo or IMPEDITIVO_OPCOES[0])
        self.entry_dt_inicio.insert(0, p.dt_inicio)
        self.entry_dt_est.insert(0, p.dt_estimada)
        self.entry_dt_ent.insert(0, p.dt_entrega)
        self.txt_obs.insert("1.0", p.observacao)
        self.entry_notas.insert(0, p.notas)

    # ------------------------------------------------------------------ #
    #  Salvar                                                              #
    # ------------------------------------------------------------------ #

    def _salvar(self):
        nome = self.entry_nome.get().strip()
        if not nome:
            messagebox.showwarning("Campos obrigatórios", "Informe o nome do projeto.", parent=self)
            return

        prio = self.combo_prio.get()
        secao_titulo = self.combo_secao.get()

        if self._is_new:
            proj = Projeto(
                linha=0,
                secao=secao_titulo,
                prio=prio,
                nome=nome,
                natureza=self.combo_natureza.get(),
                demandante=self.entry_demandante.get().strip(),
                dt_inicio=self.entry_dt_inicio.get().strip() or "-",
                dt_estimada=self.entry_dt_est.get().strip() or "-",
                dt_entrega=self.entry_dt_ent.get().strip() or "-",
                responsavel=self.entry_resp.get().strip(),
                acompanhamento=self.entry_acomp.get().strip(),
                tipo=self.combo_tipo.get(),
                status=self.combo_status.get(),
                impeditivo=self.combo_imp.get(),
                observacao=self.txt_obs.get("1.0", "end").strip(),
                notas=self.entry_notas.get().strip(),
            )
            self.sm.criar_projeto(proj)
        else:
            p = self.projeto
            p.secao = secao_titulo
            p.prio = prio
            p.nome = nome
            p.natureza = self.combo_natureza.get()
            p.demandante = self.entry_demandante.get().strip()
            p.dt_inicio = self.entry_dt_inicio.get().strip() or "-"
            p.dt_estimada = self.entry_dt_est.get().strip() or "-"
            p.dt_entrega = self.entry_dt_ent.get().strip() or "-"
            p.responsavel = self.entry_resp.get().strip()
            p.acompanhamento = self.entry_acomp.get().strip()
            p.tipo = self.combo_tipo.get()
            p.status = self.combo_status.get()
            p.impeditivo = self.combo_imp.get()
            p.observacao = self.txt_obs.get("1.0", "end").strip()
            p.notas = self.entry_notas.get().strip()
            self.sm.salvar_projeto(p)

        self.sm.save()
        if self.on_saved:
            self.on_saved()
        self.destroy()
