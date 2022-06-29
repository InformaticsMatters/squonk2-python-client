# Example that illustrates how to use the client to run a job that calculates molecular properties using RDKit.
# See here for details about the job:
# https://github.com/InformaticsMatters/virtual-screening/blob/main/data-manager/docs/rdkit/rdkit-molprops.md
#
# To run this set these environment variables (your parameters may differ):
#   export KEYCLOAK_TOKEN=`python examples/GetToken.py --keycloak-hostname keycloak.xchem-dev.diamond.ac.uk --keycloak-realm xchem --keycloak-client-id data-manager-api-dev`
#   export SQUONK_API_URL=https://data-manager.xchem-dev.diamond.ac.uk/data-manager-api
#   export PROJECT_ID=project-6c54641f-00b3-4cfa-97f7-363a7b76230a
#
# Then run like this :
#   python examples/CalcRDkitProps.py

import os
import time

from dm_api.dm_api import DmApi, DmApiRv


# token and project id are taken from environment variables...
token: str = os.environ['KEYCLOAK_TOKEN']
project_id: str = os.environ['PROJECT_ID']

if token:
    print('TOKEN OK')
else:
    print('No token provided')
    exit(1)
if project_id:
    print('PROJECT_ID OK')
else:
    print('No project_id provided')
    exit(1)

rv: DmApiRv = DmApi.ping(token)
if rv.success:
    print('API OK')
else:
    print('API not responding')
    exit(1)

rv = DmApi.put_unmanaged_project_files(token, project_id, 'examples/100.smi', project_path='/work')
if rv.success:
    print('FILE UPLOAD OK')
else:
    print('FILE UPLOAD FAILED')
    exit(1)

spec = {'collection': 'rdkit', 'job': 'rdkit-molprops', 'version': '1.0.0',
        'variables': {
            'separator': 'tab', 'outputFile': 'work/foo.smi', 'inputFile': 'work/100.smi'
        }}
rv = DmApi.start_job_instance(token, project_id, 'My Job', specification=spec)
if rv.success:
    instance_id = rv.msg['instance_id']
    task_id = rv.msg['task_id']
    print('JOB STARTED. ID=' + instance_id)
else:
    print('JOB FAILED')
    exit(1)

iterations = 0
while True:
    if iterations > 10:
        print("TIMEOUT")
        exit(1)
    rv = DmApi.get_task(token, task_id)
    if rv.msg['done']:
        break
    print('waiting ...')
    iterations += 1
    time.sleep(5)

print('DONE')

rv = DmApi.get_unmanaged_project_file(token, project_id, 'foo.smi', 'examples/foo.smi', project_path='/work')
if rv.success:
    print('DOWNLOAD OK')
else:
    print('DOWNLOAD FAILED')
    print(rv)

rv = DmApi.delete_instance(token, instance_id)
if rv.success:
    print('CLEANUP OK')
else:
    print('CLEANUP FAILED')
    print(rv)
    exit(1)