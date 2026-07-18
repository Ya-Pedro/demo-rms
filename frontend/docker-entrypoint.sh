#!/bin/sh

mkdir -p /etc/nginx/ssl

if [ -f "/etc/letsencrypt/live/pedro.ittori.ru/fullchain.pem" ]; then
    echo "Found real certificates, copying..."
    cp /etc/letsencrypt/live/pedro.ittori.ru/fullchain.pem /etc/nginx/ssl/
    cp /etc/letsencrypt/live/pedro.ittori.ru/privkey.pem /etc/nginx/ssl/
else
    echo "Real certificates not found, checking for dummy..."
    if [ ! -f "/etc/nginx/ssl/fullchain.pem" ]; then
        echo "Generating dummy certificates..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/privkey.pem -out /etc/nginx/ssl/fullchain.pem -subj '/CN=pedro.ittori.ru'
    fi
fi

exec "$@"
