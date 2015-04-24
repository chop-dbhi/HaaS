import os
import subprocess
import urllib
import time
import random
from uuid import uuid4

from flask import Flask, render_template, url_for, request, redirect, send_from_directory

app = Flask(__name__)

TEMP_DIR = 'tmp/'
METADATA_FILE = 'metadata.csv'
DATA_FILE = 'data.csv'

# Retrieve the files uploaded by the user, and if they are valid,
#  store them in a new generated subfolder of tmp/.
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return render_template('index.html')

    if request.method == 'POST':
        metadatafile = request.files['metadatafile']
        datafile = request.files['datafile']
        
        if not metadatafile or not datafile:
            render_template('index.html', missing_fields=True)

        if not metadatafile.filename.endswith('.csv') \
          or not datafile.filename.endswith('.csv'):
            render_template('index.html', wrong_filetype=True)

        print "Saving files..."
        uniqueid = str(uuid4())
        folder = os.path.join(TEMP_DIR, uniqueid)
        os.mkdir(folder)

        metadatafile.save(os.path.join(folder, METADATA_FILE))
        datafile.save(os.path.join(folder, DATA_FILE))

        return redirect(url_for('container', uuid=uniqueid))


# Generate the Docker container from the uploaded files, 
#  and redirect to the new Harvest instance.
@app.route('/containers/<uuid>')
def container(uuid):
    folder = os.path.join(TEMP_DIR, uuid)
    cidf = os.path.join(folder, 'docker.cid')
    containerid = ''
    if not os.path.exists(cidf):
        print 'Files accepted. Generating Docker Container...' 
        containerid = subprocess.check_output([
                          'docker', 'run', '-d', '-P',
                          '-v', (os.path.abspath(folder)+':/input'),
                          'dbhi/redcap-harvest'
                      ])
        containerid = containerid.strip()  # Get short container id for use in inspect
        with open(cidf, 'w') as f:
            f.write(containerid)
    else:
        with open(cidf) as f:
            containerid = f.read()

    portnumber = subprocess.check_output(
                                              ['docker','port', containerid, '8000']
                                         )
    portnumber = portnumber.split(':')[1].strip()
   
    print 'Waiting for harvest to load...' 
    harvestIP = 'http://' + os.environ['DOCKERHOST'] + ':' + portnumber
   
    for i in range(30):
        try:
            urllib.urlopen(harvestIP).getcode()
            print 'Done.'
            return redirect(harvestIP) 
        except StandardError:
            time.sleep(1)
    return 'There was a problem generating the Harvest project. \
              Pease make sure your files are valid and try again.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
