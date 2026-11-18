# One image, three jobs (pick with the command):
#   API (default)   uvicorn workhub_api.main:app
#   Worker          python -m workhub_api.worker
#   Migrations      alembic upgrade head
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /usr/local/bin/uv
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN uv sync --locked --no-dev
USER nobody
EXPOSE 8000
CMD ["uvicorn", "workhub_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
