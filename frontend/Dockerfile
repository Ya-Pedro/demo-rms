
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
        --pid-path=/tmp/nginx.pid \
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
    ln -sf /dev/stderr /var/log/nginx/error.log && \
    chown -R 1001:0 /var/cache/nginx /var/log/nginx /etc/nginx /usr/share/nginx/html && \
    chmod -R g=u /var/cache/nginx /var/log/nginx /etc/nginx /usr/share/nginx/html

RUN printf '\
load_module /usr/lib/nginx/modules/ngx_http_vhost_traffic_status_module.so;\n\
pid /tmp/nginx.pid;\n\
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

COPY build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

USER 1001

CMD ["nginx", "-g", "daemon off;"]
