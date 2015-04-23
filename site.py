import os
import subprocess
import urllib
import json
import time
import random

from flask import Flask, render_template, url_for, request, redirect, send_from_directory


app = Flask(__name__)

# Confirm that a provided file has an acceptable extension.
# In this case, '.csv' is the only allowed extension.
def allowed_file(filename):
    return ('.' in filename) and (filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS)

# Retrieve the files uploaded by the user, and if they are valid,
#  store them in a new generated subfolder of tmp/.
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        metadatafile = request.files['metadatafile']
        datafile = request.files['datafile']
        
        if not metadatafile or not datafile:
            render_template('index.html', missing_fields=True)

        if not metadatafile.filename.endswith('.csv') 
           or not datafile.filename.endswith('.csv'):
            render_template('index.html', wrong_filetype=True)

        print "Saving files..."
        app.config['UPLOAD_FOLDER'] = 'tmp/'+str(random.randint(10000,99999))+'/'
        while os.path.exists(app.config['UPLOAD_FOLDER']):
            app.config['UPLOAD_FOLDER'] = 'tmp/'+str(random.randint(10000,99999))+'/'
           
        os.mkdir(app.config['UPLOAD_FOLDER'])
        metadatafile.save(
            os.path.join(
                app.config['UPLOAD_FOLDER'],
                metadatafile.filename
            )
        )
        datafile.save(
            os.path.join(
                app.config['UPLOAD_FOLDER'],
                datafile.filename
            )
        )
        return redirect(url_for(
                            'uploaded_file', 
                            datafilename = datafile.filename, 
                            metadatafilename = metadatafile.filename
                        ))

    # If method is not 'POST' (i.e., the user has not uploaded files yet)
    #  or if files are not accepted, load the form.
    return render_template('index.html')

# Generate the Docker container from the uploaded files, 
#  and redirect to the new Harvest instance.
@app.route('/uploads/<datafilename>/<metadatafilename>')
def uploaded_file(datafilename, metadatafilename):
    print 'Files accepted. Generating Docker Container...' 
    containerid = subprocess.check_output([
                      'docker', 'run', '-d', '-P',
                      '-e', ('DATA_FILE=' + datafilename), 
                      '-e', ('METADATA_FILE=' + metadatafilename),
                      '-v', (os.path.abspath(app.config['UPLOAD_FOLDER']) + ':/input'),
                      'dbhi/redcap-harvest'
                  ])
    containerid = containerid[0:9]  # Get short container id for use in inspect
    containerinfo = json.loads(subprocess.check_output(['docker','inspect',containerid]))
   
    print 'Waiting for harvest to load...' 
    harvestIP = 'http://'+subprocess.check_output(['boot2docker', 'ip']).strip()+':'+\
                  containerinfo[0]['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort']
    while True:
        try:
            urllib.urlopen(harvestIP).getcode()
            print 'Done.'
            return redirect(harvestIP) 
        except StandardError:
            time.sleep(1)
    return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
