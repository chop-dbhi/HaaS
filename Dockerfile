FROM python:2-onbuild
MAINTAINER James Swanick "swanijam@gmail.com"

ADD site.py site.py
ADD templates templates/

RUN mkdir tmp/
ENTRYPOINT ["python", "site.py"]

EXPOSE 8000
