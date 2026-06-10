# -*- coding: utf-8 -*-
import sys
import os
import traceback
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox
import threading

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

        cred_path = self._resolver_credentials()
        self.drive_manager = DriveManager(str(cred_path)) if cred_path else None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._current_screen = None
        self._show_selector()

        # Restaurar conexão Drive em background (sem travar a UI)
        if self.drive_manager:
            threading.Thread(target=self._auto_restaurar_drive, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Handler global de exceções — evita crash silencioso                 #
    # ------------------------------------------------------------------ #

    def report_callback_exception(self, exc_type, exc_val, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        detalhe = str(exc_val) or repr(exc_val)
        messagebox.showerror(
            "Erro inesperado",
            f"Ocorreu um erro no aplicativo:\n\n{detalhe}\n\n"
            f"Detalhes técnicos:\n{msg[:600]}",
        )

    # ------------------------------------------------------------------ #
    #  Drive                                                               #
    # ------------------------------------------------------------------ #

    def _auto_restaurar_drive(self):
        try:
            ok = self.drive_manager.auto_restaurar()
            if ok:
                self.after(0, self._on_drive_restaurado)
        except Exception:
            pass

    def _on_drive_restaurado(self):
        """Chamado na thread principal quando o drive foi restaurado com sucesso."""
        if isinstance(self._current_screen, SelectorScreen):
            self._current_screen.atualizar_estado_drive()

    # ------------------------------------------------------------------ #
    #  Credenciais                                                         #
    # ------------------------------------------------------------------ #

    def _resolver_credentials(self):
        import json
        if getattr(sys, "frozen", False):
            bundled = Path(sys._MEIPASS) / "credentials.json"
            if bundled.exists():
                return bundled
        if CREDENTIALS_PATH.exists():
            return CREDENTIALS_PATH
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

    # ------------------------------------------------------------------ #
    #  Navegação                                                           #
    # ------------------------------------------------------------------ #

    def _clear(self):
        if self._current_screen:
            self._current_screen.destroy()
            self._current_screen = None

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
            drive_manager=self.drive_manager,
            on_edit=self._abrir_form_editar,
            on_new=self._abrir_form_novo,
            on_obs=self._abrir_obs,
            on_sync=self._sincronizar,
            on_voltar=self._show_selector,
            on_nova_secao=self._abrir_nova_secao,
            on_desconectar_drive=self._desconectar_drive,
        )
        screen.grid(row=0, column=0, sticky="nsew")
        self._current_screen = screen

    # ------------------------------------------------------------------ #
    #  Formulários                                                         #
    # ------------------------------------------------------------------ #

    def _abrir_form_novo(self):
        if self.sheet_manager and self.sheet_manager.mode == "generic":
            GenericForm(self, sheet_manager=self.sheet_manager,
                        row=None, on_saved=self._apos_salvar)
        else:
            ProjectForm(self, sheet_manager=self.sheet_manager,
                        projeto=None, on_saved=self._apos_salvar)

    def _abrir_form_editar(self, item):
        if self.sheet_manager and self.sheet_manager.mode == "generic":
            GenericForm(self, sheet_manager=self.sheet_manager,
                        row=item if isinstance(item, GenericRow) else None,
                        on_saved=self._apos_salvar)
        else:
            ProjectForm(self, sheet_manager=self.sheet_manager,
                        projeto=item, on_saved=self._apos_salvar)

    def _abrir_nova_secao(self):
        SectionForm(self, sheet_manager=self.sheet_manager, on_saved=self._apos_salvar)

    def _abrir_obs(self, projeto=None):
        ObsForm(self, sheet_manager=self.sheet_manager,
                projeto=projeto, on_saved=self._apos_salvar)

    def _apos_salvar(self):
        try:
            self.sheet_manager.reload()
            if isinstance(self._current_screen, ProjectListScreen):
                self._current_screen.sm = self.sheet_manager
                self._current_screen.refresh()
        except Exception as e:
            messagebox.showerror("Erro ao recarregar", str(e))

    # ------------------------------------------------------------------ #
    #  Drive                                                               #
    # ------------------------------------------------------------------ #

    def _desconectar_drive(self):
        if self.drive_manager:
            self.drive_manager.desconectar()
        self.drive_file_info = None
        self._show_selector()

    def _on_drive_desconectado(self, msg: str):
        """Sessão Drive expirou durante o uso — avisa e volta à tela inicial."""
        messagebox.showwarning(
            "Sessão Drive encerrada",
            f"{msg}\n\nVocê será redirecionado para reconectar ao Drive."
        )
        if self.drive_manager:
            self.drive_manager.service = None
        self._show_selector()

    def _sincronizar(self):
        if not self.drive_manager or not self.drive_manager.esta_autenticado():
            messagebox.showinfo("Não autenticado",
                                "Conecte ao Google Drive primeiro na tela inicial.")
            return
        if not self.drive_file_info:
            messagebox.showinfo("Arquivo local",
                                "O arquivo atual não é do Drive.\n"
                                "Abra pelo Drive para sincronizar.")
            return

        def _sync():
            from app.drive_manager import DriveDesconectadoError
            try:
                self.drive_manager.upload_atualizar(
                    self.drive_file_info["id"],
                    self.sheet_manager.filepath,
                    self.drive_file_info["mimeType"],
                )
                self.after(0, lambda: messagebox.showinfo(
                    "Sincronizado", "Planilha atualizada no Google Drive!"))
            except DriveDesconectadoError as e:
                self.after(0, lambda: self._on_drive_desconectado(str(e)))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro ao sincronizar", str(e)))

        threading.Thread(target=_sync, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
