FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R 1001:0 /app && \
    chmod -R g=u /app && \
    chmod +x entrypoint.sh

USER 1001

CMD ["./entrypoint.sh"]