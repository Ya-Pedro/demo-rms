#!/bin/sh

mkdir -p /etc/nginx/ssl

setup_cert() {
    DOMAIN=$1
    PREFIX=$2

    if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
        echo "Found real certificates for ${DOMAIN}, copying..."
        cp -L "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "/etc/nginx/ssl/${PREFIX}_fullchain.pem"
        cp -L "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" "/etc/nginx/ssl/${PREFIX}_privkey.pem"
    else
        echo "Real certificates not found for ${DOMAIN}, generating dummy..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "/etc/nginx/ssl/${PREFIX}_privkey.pem" \
            -out "/etc/nginx/ssl/${PREFIX}_fullchain.pem" \
            -subj "/CN=${DOMAIN}"
    fi
}

setup_cert "pedro.ittori.ru" "pedro"
setup_cert "rms.ittori.ru" "rms"

exec "$@"
