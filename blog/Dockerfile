FROM python:3.10-alpine3.16
LABEL maintainer="volt.awp@gmail.com"

# variales needeed for interaction with python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
WORKDIR /blog
ARG user=blog_admin
# needs to add to environment variables `CERTNAME` and `CERTKEY`
# actual values before run the image
ENV CERTNAME=
ENV CERTKEY=

# packages for connection to postgresql and other nedded packages
RUN apk update && \
    apk add --update --no-cache postgresql-client \
    build-base postgresql-dev linux-headers curl

# creating and assigning user from which will starts commands in the docker
RUN adduser -D $user && \
    addgroup $user www-data

# directory contains SSL certificate and key
RUN mkdir -p /vol/certs && \
    chown -R $user:www-data /vol/certs && \
    chmod 755 /vol/certs

USER $userS

ADD pyproject.toml poetry.lock ./

# install poetry dependency manager and all dependencies
RUN pip install --upgrade pip && \
    pip install poetry && \
    python -m poetry install --no-root

# adding path to PATH environment variable, where located applications installed through pip
ENV PATH "$PATH:/home/$user/.local/bin"

# copy source code to image
COPY . /blog
# set default shell
SHELL ["sh", "-c"]
# start uvicorn server over security connection
CMD poetry run uvicorn main:app \
    --host 0.0.0.0 --port 8000 \
    --workers 2 \
    --ssl-certfile /vol/certs/$CERTNAME \
    --ssl-keyfile /vol/certs/$CERTKEY