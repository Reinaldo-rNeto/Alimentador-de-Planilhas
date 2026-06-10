# -*- coding: utf-8 -*-
import os
import io
import json
import tempfile
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_FILE = Path.home() / ".alimentador_planilha" / "token.json"
TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)


class DriveManager:
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.service = None
        self.creds = None

    # ------------------------------------------------------------------ #
    #  Autenticação                                                        #
    # ------------------------------------------------------------------ #

    def autenticar(self) -> bool:
        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    # Token expirado sem refresh válido — refaz login
                    TOKEN_FILE.unlink(missing_ok=True)
                    creds = None

            if not creds or not creds.valid:
                if not Path(self.credentials_path).exists():
                    raise FileNotFoundError(
                        f"Arquivo credentials.json não encontrado em: {self.credentials_path}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                try:
                    creds = flow.run_local_server(
                        port=0,
                        open_browser=True,
                        timeout_seconds=120,
                        success_message=(
                            "Autenticação concluída! Pode fechar esta janela e voltar ao app."
                        ),
                    )
                except Exception as e:
                    # Timeout ou browser não abriu — tenta via console (URL manual)
                    raise RuntimeError(
                        "Não foi possível concluir a autenticação automática.\n\n"
                        "Possíveis causas:\n"
                        "• O navegador não abriu automaticamente\n"
                        "• Firewall bloqueou o redirecionamento\n"
                        "• Tempo limite atingido (2 minutos)\n\n"
                        "Solução: tente novamente. Se o navegador abrir, "
                        "conclua o login antes de 2 minutos.\n\n"
                        f"Detalhe técnico: {e}"
                    ) from e

            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        self.creds = creds
        self.service = build("drive", "v3", credentials=creds)
        return True

    def esta_autenticado(self) -> bool:
        return self.service is not None

    def desconectar(self):
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        self.service = None
        self.creds = None

    def get_usuario(self) -> str:
        if not self.service:
            return ""
        about = self.service.about().get(fields="user").execute()
        return about.get("user", {}).get("emailAddress", "")

    # ------------------------------------------------------------------ #
    #  Listar planilhas                                                    #
    # ------------------------------------------------------------------ #

    def listar_planilhas(self, query: str = "") -> list[dict]:
        """Retorna lista de {id, name, mimeType} de arquivos Excel/Sheets no Drive."""
        if not self.service:
            return []
        mime_filter = (
            "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' "
            "or mimeType='application/vnd.ms-excel' "
            "or mimeType='application/vnd.google-apps.spreadsheet'"
        )
        q = f"({mime_filter}) and trashed=false"
        if query:
            q += f" and name contains '{query}'"

        results = (
            self.service.files()
            .list(q=q, pageSize=50, fields="files(id, name, mimeType, modifiedTime)")
            .execute()
        )
        return results.get("files", [])

    # ------------------------------------------------------------------ #
    #  Download                                                            #
    # ------------------------------------------------------------------ #

    def download_para_temp(self, file_id: str, mime_type: str) -> str:
        """Baixa o arquivo para um temp file e retorna o caminho."""
        is_sheets = mime_type == "application/vnd.google-apps.spreadsheet"

        suffix = ".xlsx"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.close()

        if is_sheets:
            # Exportar como xlsx
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            request = self.service.files().get_media(fileId=file_id)

        with io.FileIO(tmp.name, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        return tmp.name

    # ------------------------------------------------------------------ #
    #  Upload / atualização                                                #
    # ------------------------------------------------------------------ #

    def upload_atualizar(self, file_id: str, filepath: str, mime_type: str):
        """Atualiza o conteúdo de um arquivo existente no Drive."""
        upload_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        media = MediaFileUpload(filepath, mimetype=upload_mime, resumable=True)
        self.service.files().update(fileId=file_id, media_body=media).execute()

    def criar_arquivo(self, nome: str, filepath: str, pasta_id: str = None) -> str:
        """Faz upload de um novo arquivo e retorna o file_id."""
        upload_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        metadata = {"name": nome}
        if pasta_id:
            metadata["parents"] = [pasta_id]
        media = MediaFileUpload(filepath, mimetype=upload_mime, resumable=True)
        f = self.service.files().create(body=metadata, media_body=media, fields="id").execute()
        return f.get("id")
