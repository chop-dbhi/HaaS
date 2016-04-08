FROM python:2-onbuild

MAINTAINER Byron Ruth "b@devel.io"

ADD site.py site.py

ADD templates templates/
ADD static static/

# The base image sets the working directory to /usr/src/app
RUN mkdir containers/

ENTRYPOINT ["python", "site.py"]

ENV DOCKER_SOCKET unix://var/run/docker.sock
ENV DOCKER_HOSTNAME localhost

VOLUME /usr/src/app/containers

EXPOSE 8000
