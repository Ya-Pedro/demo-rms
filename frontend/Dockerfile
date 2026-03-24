FROM node:20-alpine AS build
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build

FROM alpine:3.19 AS nginx_build

ENV NGINX_VERSION=1.25.4
ENV VTS_VERSION=0.2.2

RUN apk add --no-cache \
    build-base \
    linux-headers \
    openssl-dev \
    pcre-dev \
    zlib-dev \
    wget

RUN wget -q "http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz" && \
    tar -xzf "nginx-${NGINX_VERSION}.tar.gz" && \
    wget -q "https://github.com/vozlt/nginx-module-vts/archive/refs/tags/v${VTS_VERSION}.tar.gz" && \
    tar -xzf "v${VTS_VERSION}.tar.gz"

RUN cd "nginx-${NGINX_VERSION}" && \
    ./configure \
        --prefix=/etc/nginx \
        --sbin-path=/usr/sbin/nginx \
        --modules-path=/usr/lib/nginx/modules \
        --conf-path=/etc/nginx/nginx.conf \
        --error-log-path=/var/log/nginx/error.log \
        --http-log-path=/var/log/nginx/access.log \
        --pid-path=/var/run/nginx.pid \
        --with-http_ssl_module \
        --with-http_v2_module \
        --with-http_realip_module \
        --with-http_gzip_static_module \
        --with-http_stub_status_module \
        --with-threads \
        --add-dynamic-module="../nginx-module-vts-${VTS_VERSION}" \
    && make -j$(nproc) \
    && make install

FROM alpine:3.19

RUN apk add --no-cache pcre openssl zlib

COPY --from=nginx_build /usr/sbin/nginx /usr/sbin/nginx
COPY --from=nginx_build /etc/nginx /etc/nginx
COPY --from=nginx_build /usr/lib/nginx/modules /usr/lib/nginx/modules

RUN mkdir -p /var/cache/nginx /usr/share/nginx/html /etc/nginx/conf.d /var/log/nginx && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

RUN printf '\
load_module /usr/lib/nginx/modules/ngx_http_vhost_traffic_status_module.so;\n\
\n\
events {\n\
    worker_connections 1024;\n\
}\n\
\n\
http {\n\
    include       /etc/nginx/mime.types;\n\
    default_type  application/octet-stream;\n\
    sendfile      on;\n\
    keepalive_timeout 65;\n\
\n\
    vhost_traffic_status_zone;\n\
\n\
    include /etc/nginx/conf.d/*.conf;\n\
}\n' > /etc/nginx/nginx.conf

COPY --from=build /app/build /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD sh -c "\
    if [ ! -f /etc/letsencrypt/live/rms.ittori.ru/fullchain.pem ]; then \
        echo 'Local dev mode: Generating dummy SSL certs...'; \
        mkdir -p /etc/letsencrypt/live/rms.ittori.ru /etc/letsencrypt/live/grafana.rms.ittori.ru; \
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/letsencrypt/live/rms.ittori.ru/privkey.pem -out /etc/letsencrypt/live/rms.ittori.ru/fullchain.pem -subj '/CN=localhost'; \
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/letsencrypt/live/grafana.rms.ittori.ru/privkey.pem -out /etc/letsencrypt/live/grafana.rms.ittori.ru/fullchain.pem -subj '/CN=grafana.localhost'; \
    fi; \
    nginx -g 'daemon off;' \
"