FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Code is owned by root and read-only for the app user.
COPY . .

# Run as an unprivileged user. APP_UID must own the host's data folder
# (/home/ledgeradmin/ledger/data), see README "Deploying".
ARG APP_UID=1000
RUN useradd --uid ${APP_UID} --no-create-home --shell /usr/sbin/nologin ledger
USER ledger

EXPOSE 5000

CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:5000", "app:app"]
