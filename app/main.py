# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox
import threading

# Ajuste de path para importações relativas funcionarem no .exe
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

sys.path.insert(0, str(BASE_DIR))

from app.sheet_manager import SheetManager, GenericRow
from app.drive_manager import DriveManager
from app.ui.selector import SelectorScreen
from app.ui.project_list import ProjectListScreen
from app.ui.project_form import ProjectForm
from app.ui.obs_form import ObsForm
from app.ui.section_form import SectionForm
from app.ui.generic_form import GenericForm

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

CREDENTIALS_PATH = BASE_DIR / "credentials.json"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Alimentador de Planilha — GDA / ATI-PE")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color="#1E1E2E")

        self.sheet_manager: SheetManager = None
        self.drive_manager: DriveManager = None
        self.drive_file_info: dict = None

        # Inicializar Drive: tenta pasta do exe, depois config salvo
        cred_path = self._resolver_credentials()
        self.drive_manager = DriveManager(str(cred_path)) if cred_path else None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._current_screen = None
        self._show_selector()

    # ------------------------------------------------------------------ #
    #  Navegação entre telas                                               #
    # ------------------------------------------------------------------ #

    def _clear(self):
        if self._current_screen:
            self._current_screen.destroy()
            self._current_screen = None

    def _resolver_credentials(self):
        """Localiza credentials.json: embutido no exe > pasta do exe > config salvo."""
        import json, sys
        # 1. Embutido via PyInstaller (_MEIPASS = pasta temporária do bundle)
        if getattr(sys, "frozen", False):
            bundled = Path(sys._MEIPASS) / "credentials.json"
            if bundled.exists():
                return bundled
        # 2. Pasta do exe/script
        if CREDENTIALS_PATH.exists():
            return CREDENTIALS_PATH
        # 3. Caminho salvo manualmente pelo usuário
        cfg_path = Path.home() / ".alimentador_planilha" / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                saved = cfg.get("credentials_path", "")
                if saved and Path(saved).exists():
                    return Path(saved)
            except Exception:
                pass
        return None

    def _show_selector(self):
        self._clear()
        screen = SelectorScreen(
            self,
            on_file_selected=self._on_file_selected,
            drive_manager=self.drive_manager,
        )
        screen.grid(row=0, column=0, sticky="nsew")
        self._current_screen = screen

    def _on_file_selected(self, sheet_manager: SheetManager, drive_file_info: dict):
        self.sheet_manager = sheet_manager
        self.drive_file_info = drive_file_info
        self._show_project_list()

    def _show_project_list(self):
        self._clear()
        screen = ProjectListScreen(
            self,
            sheet_manager=self.sheet_manager,
            on_edit=self._abrir_form_editar,
            on_new=self._abrir_form_novo,
            on_obs=self._abrir_obs,
            on_sync=self._sincronizar,
            on_trocar_arquivo=self._show_selector,
            on_nova_secao=self._abrir_nova_secao,
        )
        screen.grid(row=0, column=0, sticky="nsew")
        self._current_screen = screen

    def _abrir_form_novo(self):
        if self.sheet_manager and self.sheet_manager.mode == "generic":
            GenericForm(
                self,
                sheet_manager=self.sheet_manager,
                row=None,
                on_saved=self._apos_salvar,
            )
        else:
            ProjectForm(
                self,
                sheet_manager=self.sheet_manager,
                projeto=None,
                on_saved=self._apos_salvar,
            )

    def _abrir_form_editar(self, item):
        if self.sheet_manager and self.sheet_manager.mode == "generic":
            GenericForm(
                self,
                sheet_manager=self.sheet_manager,
                row=item if isinstance(item, GenericRow) else None,
                on_saved=self._apos_salvar,
            )
        else:
            ProjectForm(
                self,
                sheet_manager=self.sheet_manager,
                projeto=item,
                on_saved=self._apos_salvar,
            )

    def _abrir_nova_secao(self):
        SectionForm(
            self,
            sheet_manager=self.sheet_manager,
            on_saved=self._apos_salvar,
        )

    def _abrir_obs(self, projeto=None):
        ObsForm(
            self,
            sheet_manager=self.sheet_manager,
            projeto=projeto,
            on_saved=self._apos_salvar,
        )

    def _apos_salvar(self):
        """Recarregar a lista após qualquer edição."""
        try:
            self.sheet_manager.reload()
            if isinstance(self._current_screen, ProjectListScreen):
                self._current_screen.sm = self.sheet_manager
                self._current_screen.refresh()
        except Exception as e:
            messagebox.showerror("Erro ao recarregar", str(e))

    # ------------------------------------------------------------------ #
    #  Sincronização com Google Drive                                      #
    # ------------------------------------------------------------------ #

    def _sincronizar(self):
        if not self.drive_manager:
            messagebox.showinfo(
                "Drive não configurado",
                "Coloque o arquivo credentials.json na pasta do programa para ativar o Drive.",
            )
            return
        if not self.drive_manager.esta_autenticado():
            messagebox.showinfo("Não autenticado", "Conecte ao Google Drive primeiro.")
            return
        if not self.drive_file_info:
            messagebox.showinfo(
                "Arquivo local",
                "O arquivo atual não é do Drive. Abra pelo Drive para sincronizar.",
            )
            return

        def _sync():
            try:
                self.drive_manager.upload_atualizar(
                    self.drive_file_info["id"],
                    self.sheet_manager.filepath,
                    self.drive_file_info["mimeType"],
                )
                self.after(0, lambda: messagebox.showinfo("Sincronizado", "Planilha atualizada no Google Drive!"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro ao sincronizar", str(e)))

        threading.Thread(target=_sync, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
