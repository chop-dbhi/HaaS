import os
import shutil
import time
from uuid import uuid4
from datetime import datetime
from docker import Client
from docker.errors import APIError
from flask import Flask, render_template, request, redirect, \
    send_from_directory


app = Flask(__name__, static_url_path='')

# Default timeout for checking if a container is ready.
DEFAULT_TIMEOUT = 120

# Directory on the host that new containers will mount.
HOST_CONTAINER_DIR = os.environ['CONTAINER_DIR']

# Name of the local directory containing the container
# directories.
CONTAINER_DIR = 'containers'

# Standard names for the uploaded REDCap metadata and data files.
METADATA_FILE = 'metadata.csv'
DATA_FILE = 'data.csv'

# Name of the
CID_FILE = 'docker.cid'

# Docker socket and hostname for public URLs.
DOCKER_SOCKET = os.environ.get('DOCKER_SOCKET')
DOCKER_HOSTNAME = os.environ.get('DOCKER_HOSTNAME')

# Initialize the docker client
docker = Client(base_url=DOCKER_SOCKET)


@app.route('/static/<path>', methods=['GET'])
def serve_static(path):
    return send_from_directory('static', path)


# Retrieve the files uploaded by the user, and if they are valid,
# store them in a subfolder in the containers directory.
@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('index.html')

    metadatafile = request.files['metadatafile']
    datafile = request.files['datafile']

    if not metadatafile or not datafile:
        return render_template('index.html', missing_fields=True)

    if not metadatafile.filename.endswith('.csv') \
            or not datafile.filename.endswith('.csv'):
        return render_template('index.html', wrong_filetype=True)

    uuid = str(uuid4())
    folder = os.path.join(CONTAINER_DIR, uuid)
    os.mkdir(folder)

    metadatafile.save(os.path.join(folder, METADATA_FILE))
    datafile.save(os.path.join(folder, DATA_FILE))

    url = launch_container(uuid)

    if url:
        return redirect(url)

    return 'There was a problem running the container', 500


@app.route('/containers')
def list_containers():
    items = []

    for name in os.listdir(CONTAINER_DIR):
        path = os.path.join(CONTAINER_DIR, name)

        if not os.path.isdir(path):
            continue

        uuid = os.path.basename(name)

        cid = container_id(uuid) or ''

        created = ''
        uptime = ''
        url = ''
        status = 'Starting'

        if cid:
            port = container_port(cid)
            info = container_info(cid)

            if info:
                if info['State']['Running']:
                    # Ignore nanosecond resolution.
                    created = info['Created'].split('.')[0]

                    if container_ready(cid, timeout=1):
                        url = container_redirect(port)
                        status = 'Running'
                        created_time = datetime.strptime(created,
                                                         '%Y-%m-%dT%H:%M:%S')
                        uptime = datetime.now() - created_time
                    else:
                        status = 'Building'
                else:
                    status = 'Not Running'
            else:
                status = 'Missing'

        items.append({
            'url': url,
            'cid': cid[:16],
            'uuid': uuid,
            'status': status,
            'created': created,
            'uptime': uptime,
        })

    return render_template('list.html', containers=items)


@app.route('/containers/<cid>/remove', methods=['POST'])
def remove(cid):
    folder_name = (container_info(cid))['Name']
    shutil.rmtree(os.path.join(CONTAINER_DIR , (folder_name.split('/'))[1]))
    docker.stop(cid)
    docker.remove_container(cid)
    return redirect('/containers')


@app.route('/containers/<cid>/stop', methods=['POST'])
def stop(cid):
    docker.stop(cid)
    return redirect('/containers')


@app.route('/containers/<cid>/start', methods=['POST'])
def start(cid):
    docker.start(cid)
    while not container_ready(cid, timeout=1):
        time.sleep(0.5)
    return redirect('/containers')


@app.route('/containers/<uuid>')
def container(uuid):
    url = launch_container(uuid)

    if url:
        return redirect(url)

    return 'There was a problem running the container', 500


def launch_container(uuid):
    "Launches a container returning the public URL."
    cid = container_id(uuid)

    if not cid:
        cid = run_container(uuid)

    port = container_port(cid)

    if container_ready(cid):
        return container_redirect(port)


def container_id(uuid):
    folder = os.path.join(CONTAINER_DIR, uuid)
    cidf = os.path.join(folder, CID_FILE)

    if os.path.exists(cidf):
        with open(cidf) as f:
            return f.read().strip()


def run_container(uuid):
    "Runs a container given a UUID."
    folder = os.path.join(CONTAINER_DIR, uuid)
    cidf = os.path.join(folder, CID_FILE)

    # Create config
    config = {
        'name': uuid,
        'image': 'dbhi/redcap-harvest',
        'detach': True,
        'ports': [8000],
        'labels': {
            'redcap-harvest': uuid,
        },
        'volumes': [
            '/input',
        ],
    }

    container = docker.create_container(**config)

    cid = container['Id']

    with open(cidf, 'w') as f:
        f.write(cid)

    # Run parameters
    params = {
        'port_bindings': {
            8000: None,
        },
        'binds': {
            os.path.join(HOST_CONTAINER_DIR, uuid): {
                'bind': '/input',
                'ro': False,
            }
        },
        'restart_policy': {
            'MaximumRetryCount': 3,
            'Name': 'always',
        }
    }

    docker.start(cid, **params)

    return cid


def container_info(cid):
    "Returns info about the container."
    try:
        return docker.inspect_container(cid)
    except APIError:
        pass


def container_port(cid):
    "Returns the port of the container."
    try:
        ports = docker.port(cid, 8000)
    except APIError:
        return

    if not ports:
        return

    return ports[0]['HostPort']


def container_redirect(port):
    "Returns the public address given the container ID."
    return 'http://{}:{}'.format(DOCKER_HOSTNAME, port)


def container_ready(cid, timeout=DEFAULT_TIMEOUT):
    "Returns true if the container is deemed ready for end user use."

    # Lightweight cURL command to test the status code of the
    # running container.
    cmd = ['curl', '-s', '-o', '/dev/null', '-I',
           '-w', '%{http_code}', 'localhost:8000']

    exec_id = docker.exec_create(cid, cmd=cmd)['Id']

    for _ in range(timeout):
        resp = docker.exec_start(exec_id)

        if resp == '200':
            return True

        time.sleep(0.5)

    return False


if __name__ == '__main__':
    debug = bool(os.environ.get('DEBUG'))

    app.run(host='0.0.0.0',
            port=8000,
            threaded=True,
            debug=debug)
