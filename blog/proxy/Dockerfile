FROM nginx:stable-alpine
LABEL maintainer="volt.awp@gmail.com"
ARG user=nginx

# directories for media and static files
# creating pid file for nginx
RUN mkdir -p /vol/certs

# copying configs
COPY ./nginx_ssl.conf.template ./run.sh /etc/nginx/
COPY ./192.168.59.100-key.pem ./192.168.59.100.pem /vol/certs/

RUN chmod +x /etc/nginx/run.sh

# setting owner and permissions for folder with certificate
RUN chown -R $user:www-data /vol && chmod -R 755 /vol

# adding user to the group
RUN addgroup $user www-data

CMD ["/etc/nginx/run.sh"]
