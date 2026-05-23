# syntax=docker/dockerfile:1.7
#
# Ragent Python backend image.
#
# Two-stage build:
#   * builder  installs the project + its declared dependencies into a
#              throw-away `/install` prefix using the project's own
#              `pyproject.toml` as the single source of truth.
#   * runtime  is a clean python:3.12-slim layer that only carries the
#              installed site-packages + entry-point scripts. No pip,
#              no source tree, no build tools end up in the final
#              image.
#
# The resulting runtime image runs as a non-root user, exposes :8000,
# and has a self-contained HEALTHCHECK against /healthz so docker
# compose can serialize startup behind `condition: service_healthy`.

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Copy build inputs. README is referenced by pyproject.toml's `readme`
# field; setuptools' source dist build refuses to run without it.
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --prefix=/install .

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHON_HOST=0.0.0.0 \
    PYTHON_PORT=8000 \
    PYTHON_INGESTION_SQLITE_PATH=/home/app/data/ingestion.db

# Copy the install prefix from the builder onto the runtime's
# /usr/local. Scripts (e.g. uvicorn) land in /usr/local/bin and
# packages land in /usr/local/lib/python3.12/site-packages.
COPY --from=builder /install /usr/local

RUN groupadd --system app \
    && useradd --system --gid app --uid 1001 --home /home/app --shell /usr/sbin/nologin app \
    && mkdir -p /home/app/data \
    && chown -R app:app /home/app

USER app
WORKDIR /home/app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=6 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).status == 200 else 1)" || exit 1

CMD ["python", "-m", "uvicorn", "ragent_python.main:app", "--host", "0.0.0.0", "--port", "8000"]
