# -*- coding: utf-8 -*-
import io
import tempfile
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_FILE = Path.home() / ".alimentador_planilha" / "token.json"
TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)


class DriveDesconectadoError(Exception):
    """Lançada quando a sessão Drive expirou e não é possível renovar automaticamente."""


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
                    TOKEN_FILE.unlink(missing_ok=True)
                    creds = None

            if not creds or not creds.valid:
                if not Path(self.credentials_path).exists():
                    raise FileNotFoundError(
                        f"credentials.json não encontrado em: {self.credentials_path}"
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
                    raise RuntimeError(
                        "Não foi possível concluir a autenticação automática.\n\n"
                        "Possíveis causas:\n"
                        "• O navegador não abriu automaticamente\n"
                        "• Firewall bloqueou o redirecionamento\n"
                        "• Tempo limite atingido (2 minutos)\n\n"
                        "Tente novamente. Se o navegador abrir, "
                        "conclua o login antes de 2 minutos.\n\n"
                        f"Detalhe técnico: {e}"
                    ) from e

            self._salvar_token(creds)

        self.creds = creds
        self.service = build("drive", "v3", credentials=creds)
        return True

    def auto_restaurar(self) -> bool:
        """Restaura do token salvo sem abrir browser. Retorna True se ok."""
        if not TOKEN_FILE.exists():
            return False
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            if creds and creds.valid:
                self.creds = creds
                self.service = build("drive", "v3", credentials=creds)
                return True
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self._salvar_token(creds)
                self.creds = creds
                self.service = build("drive", "v3", credentials=creds)
                return True
        except Exception:
            TOKEN_FILE.unlink(missing_ok=True)
        return False

    def esta_autenticado(self) -> bool:
        return self.service is not None

    def desconectar(self):
        TOKEN_FILE.unlink(missing_ok=True)
        self.service = None
        self.creds = None

    def get_usuario(self) -> str:
        if not self.service:
            return ""
        about = self._executar(
            lambda: self.service.about().get(fields="user").execute()
        )
        return about.get("user", {}).get("emailAddress", "")

    # ------------------------------------------------------------------ #
    #  Helpers internos                                                    #
    # ------------------------------------------------------------------ #

    def _salvar_token(self, creds):
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    def _renovar_token(self):
        """Renova access_token usando o refresh_token. Lança DriveDesconectadoError se falhar."""
        if not self.creds or not self.creds.refresh_token:
            self.service = None
            raise DriveDesconectadoError(
                "Sessão do Google Drive expirou e não há refresh token salvo.\n"
                "Conecte ao Drive novamente."
            )
        try:
            self.creds.refresh(Request())
            self._salvar_token(self.creds)
            # Reconstrói o service com as credenciais atualizadas
            self.service = build("drive", "v3", credentials=self.creds)
        except (RefreshError, TransportError) as e:
            TOKEN_FILE.unlink(missing_ok=True)
            self.service = None
            self.creds = None
            raise DriveDesconectadoError(
                "A sessão do Google Drive foi encerrada.\n\n"
                "Possíveis causas:\n"
                "• Sem conexão com a internet\n"
                "• Acesso revogado nas configurações do Google\n"
                "• Token expirado e renovação falhou\n\n"
                "Solução: conecte ao Drive novamente na tela inicial.\n\n"
                f"Detalhe: {e}"
            ) from e

    def _garantir_token_valido(self):
        """Garante que o token está válido antes de uma chamada à API."""
        if not self.service:
            raise DriveDesconectadoError("Drive não autenticado.")
        if self.creds and self.creds.expired:
            self._renovar_token()

    def _executar(self, chamada):
        """
        Executa uma chamada à API com retry automático em expiração de token.
        `chamada` deve ser um callable sem argumentos que retorna o resultado.
        """
        self._garantir_token_valido()
        try:
            return chamada()
        except HttpError as e:
            if e.status_code in (401, 403):
                # Token pode ter expirado entre a verificação e a execução
                self._renovar_token()
                return chamada()
            raise
        except Exception as e:
            # Erros de rede — tenta renovar e reintentar uma vez
            if "ssl" in str(e).lower() or "connection" in str(e).lower():
                self._renovar_token()
                return chamada()
            raise

    # ------------------------------------------------------------------ #
    #  Listar planilhas                                                    #
    # ------------------------------------------------------------------ #

    def listar_planilhas(self, query: str = "") -> list[dict]:
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

        results = self._executar(
            lambda: self.service.files()
            .list(q=q, pageSize=50, fields="files(id, name, mimeType, modifiedTime)")
            .execute()
        )
        return results.get("files", [])

    # ------------------------------------------------------------------ #
    #  Download                                                            #
    # ------------------------------------------------------------------ #

    def download_para_temp(self, file_id: str, mime_type: str) -> str:
        self._garantir_token_valido()

        is_sheets = mime_type == "application/vnd.google-apps.spreadsheet"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        tmp.close()

        try:
            if is_sheets:
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
        except HttpError as e:
            if e.status_code in (401, 403):
                # Renova e recria o request (não pode reutilizar o request antigo)
                self._renovar_token()
                if is_sheets:
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
            else:
                raise

        return tmp.name

    # ------------------------------------------------------------------ #
    #  Upload / atualização                                                #
    # ------------------------------------------------------------------ #

    def upload_atualizar(self, file_id: str, filepath: str, mime_type: str):
        self._garantir_token_valido()
        upload_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        media = MediaFileUpload(filepath, mimetype=upload_mime, resumable=True)
        try:
            self._executar(
                lambda: self.service.files()
                .update(fileId=file_id, media_body=media)
                .execute()
            )
        except Exception:
            # Recria media para retry (MediaFileUpload não é reutilizável após falha)
            media2 = MediaFileUpload(filepath, mimetype=upload_mime, resumable=True)
            self.service.files().update(fileId=file_id, media_body=media2).execute()

    def criar_arquivo(self, nome: str, filepath: str, pasta_id: str = None) -> str:
        self._garantir_token_valido()
        upload_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        metadata = {"name": nome}
        if pasta_id:
            metadata["parents"] = [pasta_id]
        media = MediaFileUpload(filepath, mimetype=upload_mime, resumable=True)
        f = self._executar(
            lambda: self.service.files()
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )
        return f.get("id")
