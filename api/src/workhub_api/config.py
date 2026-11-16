from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Read from environment or .env; never hard-code secrets (NFSD SEC-06).

    Defaults match the local Docker Postgres, so CI and `docker compose up db` work unchanged.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "workhub"
    postgres_password: str = "workhub"
    postgres_db: str = "workhub"
    postgres_sslmode: str = "prefer"  # Azure needs "require"

    # Temporary until Entra sign-in (WH-04): accept an X-User-Id header. Must be off in production.
    dev_auth: bool = False

    # Microsoft Entra sign-in (WH-04). Both come from the app registration's Overview page.
    entra_tenant_id: str = ""
    entra_client_id: str = ""

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters in the password.
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query={"sslmode": self.postgres_sslmode},
        )


settings = Settings()
