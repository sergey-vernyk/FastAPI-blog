FROM python:3.10-alpine3.16
LABEL maintainer="volt.awp@gmail.com"

# variales needeed for interaction with python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

EXPOSE 8000
WORKDIR /blog
ARG user=blog_admin

# packages for connection to postgresql and other nedded packages
RUN apk update && \
    apk add --update --no-cache postgresql-client \
        build-base postgresql-dev linux-headers curl

# creating and assigning user from which will starts commands in the docker
RUN adduser -D $user && \
    addgroup $user www-data

USER $user

# install dependencies
RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# adding path to PATH environment variable, where located applications installed through pip
ENV PATH "$PATH:/home/$user/.local/bin"

# copy source code to docker
COPY . /blog
# start uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]