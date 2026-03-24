FROM alpine:3.19

RUN apk add --no-cache postgresql-client aws-cli bash tzdata

ENV TZ=Europe/Moscow

WORKDIR /app

COPY backup.sh /app/backup.sh
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/backup.sh /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
