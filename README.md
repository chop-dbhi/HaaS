# Harvest as a Service

A Dockerized web form used to convert REDCap datafiles into a Harvest project, and deploy a server to provide access to it.

Installation and Setup
----------------------

This tool runs using Docker. Install it if you don't have it:

[Install Docker](http://docs.docker.com/installation/) 



Once you have Docker, execute the following command:

For Non-Mac:
```bash
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -v /usr/src/app/tmp:/usr/src/app/tmp -v $(which docker):/usr/bin/docker -e DOCKER_HOST=$($HOSTNAME | ip route|awk '/default/ { print  $3}') --add-host dockerhost:`ip route|awk '/default/ { print  $3}'` -p 8000:8000 swanijam/flask-harvest
```

For Mac:
```bash
docker run -it --rm -v /var/run/docker.sock:/var/run/docker.sock -v /usr/src/app/tmp:/usr/src/app/tmp -v $(which docker):/usr/bin/docker -e DOCKER_HOST=$(boot2docker ip) --add-host dockerhost:$(boot2docker ip) -p 8000:8000 swanijam/flask-harvest
```


- -it causes it to be run as an interactive terminal on the command line.
- --rm causes it to be removed when the flask container is stopped.
- -v  /var/run/docker.sock:/var/run/docker.sock mounts the hosts' docker socket on the 
      flask container, allowing the flask container to run new docker containers
      on the host.
- -v $(which docker):/usr/bin/docker mounts the docker binary in the flask container
          is also necessary for the flask container to run new docker containers. 
- -v /usr/src/app/tmp:/usr/src/app/tmp mounts the host's /tmp folder to the flask 
          container's /tmp folder, so that when the containers flask runs write to /tmp,           those changes are reflected on the host filesystem.
- -e DOCKERHOST provides the flask container with the ip of the dockerhost so that it can          redirect 
- --add-host dockerhost creates a new host named dockerhost that is accessible by the
         flask container.
- -p 8000:8000 maps the containers port 8000 to the host's port 8000 so that the containe         r's server can be accessed from the host. change the first '8000' if you wanted          to use a different host port.
- swanijam/flask-harvest is the name of the docker image that runs the Flask container.

Now find the ip of your docker host:
For Non-Mac:
```bash
ip route|awk '/default/ { print  $3}'
```
For Mac:
```bash
boot2docker ip
```
Then visit <dockerhost>:8000 to view the form.  
