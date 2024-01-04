#!/bin/sh

set -e

# Avoid replacing these with envsubst
export host=\$host
export request_uri=\$request_uri
export scheme=\$scheme

# set custom nginx config as default
envsubst </etc/nginx/nginx_ssl.conf.template >/etc/nginx/conf.d/default.conf
# starting nginx
nginx -g 'daemon off;'
