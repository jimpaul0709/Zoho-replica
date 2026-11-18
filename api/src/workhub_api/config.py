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
    postgres_sslmode: str = (
        "prefer"  # Azure needs "require"; "verify-full" also checks the certificate
    )
    postgres_sslrootcert: str | None = None  # path to Azure's root CA file, for "verify-full"

    # Temporary dev sign-in (v1 will be email + password, v2 Microsoft Entra ID): accept an
    # X-User-Id header. Must be off in production.
    dev_auth: bool = False

    # Where the web app runs (CORS). Vite's default port.
    web_origin: str = "http://localhost:5173"

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters in the password.
        query = {"sslmode": self.postgres_sslmode}
        if self.postgres_sslrootcert:
            query["sslrootcert"] = self.postgres_sslrootcert
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query=query,
        )


settings = Settings()
