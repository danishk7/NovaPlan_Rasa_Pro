# Dockerfile — NovaPlan Rasa Pro CALM + APIs | Hugging Face Spaces | public port 8501
FROM rasa/rasa-pro:3.12.42

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        supervisor \
        nginx \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        "rasa-sdk==3.12.0" \
        "streamlit>=1.35,<2.0" \
        "fastapi>=0.111,<1.0" \
        "uvicorn[standard]>=0.27,<0.30" \
        "httpx>=0.27" \
        "requests>=2.32" \
        "python-dotenv>=1.0" \
        "huggingface-hub>=0.23" \
        "tenacity>=8.3" \
        "aiohttp>=3.9" \
        "sse-starlette>=2.1" \
        "psycopg[binary]>=3.1" \
        "psycopg-pool>=3.2" \
        "pydantic>=2.0" \
        "email-validator>=2.1" \
        "bcrypt>=4.0" \
        "PyJWT>=2.8"

WORKDIR /app

COPY rasa/                       /app/rasa/
COPY api/                        /app/api/
COPY db/                         /app/db/
COPY config/                     /app/config/
COPY tests/                      /app/tests/
COPY hf_proxy.py                 /app/hf_proxy.py
COPY ui/                         /app/ui/
COPY pytest.ini                  /app/pytest.ini
COPY requirements-test.txt       /app/requirements-test.txt
COPY docs/TESTING_README.md      /app/docs/TESTING_README.md
COPY docs/RASA_TESTING_README.md /app/docs/RASA_TESTING_README.md
COPY scripts/start_hf.sh         /app/scripts/start_hf.sh
COPY scripts/train_rasa.sh       /app/scripts/train_rasa.sh
COPY scripts/run_rasa.sh         /app/scripts/run_rasa.sh
COPY scripts/run_tests.sh        /app/scripts/run_tests.sh
COPY scripts/generate_test_evidence.py /app/scripts/generate_test_evidence.py
COPY supervisord.conf            /etc/supervisor/conf.d/novaplan.conf

RUN pip install --no-cache-dir -r /app/requirements-test.txt

RUN mkdir -p \
        /app/rasa/models \
        /app/results \
        /var/log/supervisor \
        /var/log/nginx \
        /tmp/nginx_client_body \
        /tmp/nginx_proxy \
        /tmp/nginx_fastcgi \
        /tmp/nginx_uwsgi \
        /tmp/nginx_scgi \
        /tmp/novaplan_data \
    && chmod +x /app/scripts/start_hf.sh /app/scripts/train_rasa.sh /app/scripts/run_rasa.sh /app/scripts/run_tests.sh \
    && chown -R 1000:1000 \
        /app \
        /var/log/supervisor \
        /var/log/nginx \
        /tmp/nginx_client_body \
        /tmp/nginx_proxy \
        /tmp/nginx_fastcgi \
        /tmp/nginx_uwsgi \
        /tmp/nginx_scgi \
        /tmp

USER 1000

EXPOSE 8501

ENTRYPOINT []
CMD ["/app/scripts/start_hf.sh"]
