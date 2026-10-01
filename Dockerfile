FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ovos-translate-server \
                               ovos-translate-server-plugin

ENV XDG_CONFIG_HOME=/config
WORKDIR /app

EXPOSE 9686

ENTRYPOINT ["ovos-translate-server", "--host", "0.0.0.0", "--port", "9686"]
