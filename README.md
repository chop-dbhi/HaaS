# Harvest as a Service

A service for creating and deploying Harvest applications from REDCap projects with a simple web form.

The service presents a web form for uploading a REDCap data dictionary and data file. Upon upload, the files will be used to generate a Harvest application that is modeled after the REDCap data. Once the application is ready it will be deployed on the host at a specific endpoint and the user will be redirected to the Harvest interface.

## Setup

The service requires [Docker](http://docs.docker.com) for building and deploying Harvest application containers. Ensure Docker is [installed](http://docs.docker.com/installation/) and working correctly.


This service builds and runs containers use the `dbhi/redcap-harvest` image. It is recommended to pull the image before launchingn the service, so the first user does not need to wait for the image to download.

```bash
docker pull dbhi/redcap-harvest
```

## Run

This service runs in a container itself and requires access to the Docker binary and socket on the host so Harvest containers built and run. In addition, the host IP address must be added as a host to this service to make it able to check if the built container is successfully handling requests.

OS X users are assumed to be using [boot2docker](https://docs.docker.com/installation/mac/) which require slightly different arguments.

Set the `DOCKER_IP` (or set it manually).

```bash
if hash boot2docker 2>/dev/null; then
    DOCKER_IP=$(boot2docker ip)
else
    DOCKER_IP=$($HOSTNAME | ip route|awk '/default/ { print  $3}')
fi
```

```bash
docker run \
    --add-host dockerhost:$DOCKER_IP \
    -e DOCKER_IP=$DOCKER_IP \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $(which docker):/usr/bin/docker \
    -v /usr/src/app/containers:/usr/src/app/containers \
    -p 8000:8000 \
    dbhi/haas
```

Arguments:

- `--add-host dockerhost:$DOCKER_IP` is required so this container can make requests to the newly built container (from within the container).
- THe `DOCKER_IP` environment variable is used for the redirect to the newly running app. This IP or hostname must be accessible by the end user.
- The `/var/run/docker.sock:/var/run/docker.sock` volume is required the host's Docker socket in this container which make it possible to build and run new containers.
- The `$(which docker):/usr/bin/docker` volume is required and makes the host's Docker binary available in the container to access the client commands.
- The `/usr/src/app/tmp:/usr/src/app/tmp` volume is required so files uploaded for the built containers are accessible by the container on the host system itself, *not* in this service container.
- Port 8000 is exposed by this container.
