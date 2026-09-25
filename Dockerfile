FROM mcr.microsoft.com/dotnet/sdk:6.0

# install ilspycmd
RUN dotnet tool install ilspycmd -g --version 8.2.0.7535
ENV PATH "$PATH:/root/.dotnet/tools"

# install uv (provides its own managed python)
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /usr/local/bin/
ENV UV_PYTHON_PREFERENCE=only-managed \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# prepare python project
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen

CMD ["python3", "/app/app.py"]
