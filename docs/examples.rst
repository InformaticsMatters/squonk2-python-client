########
Examples
########
Some examples illustrating the basics of the API.

You can find the source code and data files for these examples in
the ``examples`` directory of the `data-manager-api`_ repository.

********
GetToken
********
An example that illustrates how to use the client get a token
that can be used in other examples.

.. literalinclude:: ../examples/GetToken.py
    :language: python

.. note::
    Tokens typically have a limited lifespan and you may need to regenerate
    it at intervals.

To run this example set these environment variables
(your parameters may differ): -

.. code-block:: bash

    export DMAPI_USERNAME=<keycloak username>
    export DMAPI_PASSWORD=<keycloak password>

Then run it like this, storing the token in the ``KEYCLOAK_TOKEN``
environment variable: -

.. code-block:: bash

    KEYCLOAK_TOKEN=$(./examples/GetToken.py \
        --keycloak-hostname keycloak.xchem-dev.diamond.ac.uk \
        --keycloak-realm xchem \
        --keycloak-client-id data-manager-api-dev)

**************
CalcRDKitProps
**************
An example that illustrates how to use the client to run a job that
Illustrates how to: -

- Upload a file
- Run a simple job (with options) using that file
- Wait for the job to complete
- Download the results and, finally...
- Cleanup (delete) the job instance

It uploads a ``.smi`` file, a text file containing lines of tab-separated
**SMILES** and a **Compound ID** strings. The one used here can be found
in the examples directory of this repository.

This example calculates molecular properties using RDKit and uses
the **rdkit-molprops** Job, which is typically available on a DM server.

Read the `rdkit-molprops`_ documentation in our **Virtual Screening** collection
for further details.

.. literalinclude:: ../examples/CalcRDKitProps.py
    :language: python

Assuming you've set a token in the environment variable ``KEYCLOAK_TOKEN``
set these additional environment variables (your parameters may differ): -

.. code-block:: bash

    export SQUONK_API_URL=https://data-manager.xchem-dev.diamond.ac.uk/data-manager-api
    export PROJECT_ID=project-6c54641f-00b3-4cfa-97f7-363a7b76230a
    export JOB_INPUT=examples/100.smi

Then run the example like this :

.. code-block:: bash

    ./examples/CalcRDKitProps.py

.. _rdkit-molprops: https://github.com/InformaticsMatters/virtual-screening/blob/main/data-manager/docs/rdkit/rdkit-molprops.md
.. _data-manager-api: https://github.com/InformaticsMatters/data-manager-api
