FROM python:2-onbuild
MAINTAINER James Swanick "swanijam@gmail.com"

ADD site.py site.py
ADD templates templates/

RUN mkdir tmp/
ENTRYPOINT ["python", "site.py"]

ENV DOCKERHOST = "192.168.59.103"

EXPOSE 8000
