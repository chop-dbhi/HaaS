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

This service runs in a container itself and requires access to the Docker binary and socket on the host so Harvest containers built and run. In addition, the Docker hostname or IP address must be passed so a proper redirect URL can be constructed.

OS X users are assumed to be using [docker-machine](https://docs.docker.com/machine/) which require slightly different arguments.

Set the `DOCKER_HOSTNAME` (or set it manually).

```bash
if hash docker-machine 2>/dev/null; then
    DOCKER_HOSTNAME=$(docker-machine ip)
else
    DOCKER_HOSTNAME=$($HOSTNAME | ip route | awk '/default/ { print  $3}')
fi
```

Define a shared directory on the host for storing files used to build the containers:

```bash
CONTAINER_DIR=/opt/haas/containers
```

```bash
docker run \
    -e DOCKER_HOSTNAME=$DOCKER_HOSTNAME \
    -e CONTAINER_DIR=$CONTAINER_DIR \
    -v $CONTAINER_DIR:/usr/src/app/containers \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -p 8000:8000 \
    dbhi/haas
```

Arguments:

- The `DOCKER_HOSTNAME` environment variable is used creating the redirect URL to the newly running Harvest container. This must be accessible to the end user.
- The `CONTAINER_DIR` environment variable specifies a shared folder for storing uploaded files which will be mounted by the redcap-harvest containers.
- The `/var/run/docker.sock:/var/run/docker.sock` volume is required the host's Docker socket in this container which make it possible to build and run new containers.
- The `$CONTAINER_DIR:/usr/src/app/containers` volume is required so files uploaded for the built containers are accessible by the container on the host system itself, *not* in this service container.
- Port 8000 is exposed by this container.
