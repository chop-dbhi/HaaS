import os
import time
import urllib
from uuid import uuid4
from datetime import datetime
from docker import Client
from flask import Flask, render_template, request, redirect, \
    send_from_directory


app = Flask(__name__, static_url_path='')

DOCKER_IP = os.environ['DOCKER_IP']
DEBUG = os.environ.get('DEBUG')
CONTAINERS_DIR = 'containers'
METADATA_FILE = 'metadata.csv'
DATA_FILE = 'data.csv'
CID_FILE = 'docker.cid'
DEFAULT_TIMEOUT = 60


docker = Client(base_url='unix://var/run/docker.sock')


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
    folder = os.path.join(CONTAINERS_DIR, uuid)
    os.mkdir(folder)

    metadatafile.save(os.path.join(folder, METADATA_FILE))
    datafile.save(os.path.join(folder, DATA_FILE))

    addr = launch_container(uuid)

    if addr:
        return redirect(addr)

    return 'There was a problem running the container', 500


@app.route('/containers')
def list_containers():
    items = []

    for name in os.listdir(CONTAINERS_DIR):
        path = os.path.join(CONTAINERS_DIR, name)

        if not os.path.isdir(path):
            continue

        uuid = os.path.basename(name)

        cid = container_id(uuid) or ''

        created = ''
        uptime = ''
        url = ''
        status = 'Starting'

        if cid:
            url = container_addr(cid)

            info = container_info(cid)

            # Ignore nanosecond resolution.
            created = info['Created'].split('.')[0]

            if poll_container(url, timeout=1):
                status = 'Running'
                created_time = datetime.strptime(created, '%Y-%m-%dT%H:%M:%S')
                uptime = datetime.now() - created_time
            else:
                status = 'Building'

        items.append({
            'url': url,
            'cid': cid[:16],
            'uuid': uuid,
            'status': status,
            'created': created,
            'uptime': uptime,
        })

    return render_template('list.html', containers=items)


@app.route('/containers/<uuid>')
def container(uuid):
    addr = launch_container(uuid)

    if addr:
        return redirect(addr)

    return 'There was a problem running the container', 500


def launch_container(uuid):
    "Launches a container returning the address."
    cid = container_id(uuid)

    if not cid:
        cid = run_container(uuid)

    addr = container_addr(cid)

    if poll_container(addr):
        return addr


def container_id(uuid):
    folder = os.path.join(CONTAINERS_DIR, uuid)
    cidf = os.path.join(folder, CID_FILE)

    if os.path.exists(cidf):
        with open(cidf) as f:
            return f.read().strip()


def run_container(uuid):
    "Runs a container given a UUID."
    folder = os.path.join(CONTAINERS_DIR, uuid)
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
        ]
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
            os.path.abspath(folder): {
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
    return docker.inspect_container(cid)


def container_addr(cid):
    "Returns the public address given the container ID."
    ports = docker.port(cid, 8000)

    if not ports:
        return

    port = ports[0]['HostPort']

    return 'http://{}:{}'.format(DOCKER_IP, port)


def poll_container(addr, timeout=DEFAULT_TIMEOUT):
    "Polls the address until it returns a successful response code."
    for _ in range(timeout):
        try:
            urllib.urlopen(addr).getcode()
            return True
        except StandardError:
            time.sleep(1)

    return False


if __name__ == '__main__':
    debug = bool(DEBUG)

    app.run(host='0.0.0.0',
            port=8000,
            threaded=True,
            debug=debug)
