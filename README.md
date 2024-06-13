# Projektarbeit RWTH Digitaler Zwilling
This project aims to demonstrate the benefits of digital twins and AAS on an actual test plant at the ITA Group International Centre for Sustainable Textiles RWTH Aachen.

# English:
This repository contains a python script that saves Asset Administration Shells (AAS) in CouchDB as supported by the [BaSyx Python SDK](https://github.com/eclipse-basyx/basyx-python-sdk). The AASX files were created in the [AAS Manager](https://github.com/rwth-iat/aas_manager) GUI and contain submodels such as sustainability, Contact Information and the machine state. After saving the AASX files in the CouchDB repository for persistent value storage, the Python script enters a timed loop which fetches the data from an OPC UA Server provided by the assembly line present at the Faculty and subsequently writes it to the CouchDB repository for further use by other software.

The program looks for a submodel called machine_state in all AASX files loaded and iterates over all properties in that submodel. If OPC UA returns a value for the property, it is updated, if not, the property is skipped.

To improve performance if larger submodels need to be synchronized, the [new Python OPC UA client](https://github.com/FreeOpcUa/opcua-asyncio) should be used, which supports asynchronous requests and coudl thus update the property values concurrently, drastically reducing iteration time.

# Deutsch:
Diese Repository enthält ein Python-Skript, das Asset Administration Shells / Verwaltungsschalen (AAS) in CouchDB speichert, wie vom BaSyx Python SDK empfohlen. Die AASX-Dateien wurden im AAS Manager GUI erstellt und enthalten Submodelle wie Nachhaltigkeit, Kontaktinformationen und den Maschinenzustand. Nachdem die AASX-Dateien in der CouchDB-Repository gespeichert wurden, startet das Python-Skript eine getaktete Schleife, die die Daten von einem OPC UA-Server abruft, der von der Montagelinie an der Fakultät bereitgestellt wird, und sie anschließend in der CouchDB-Repository für die weitere Verwendung durch andere Software speichert.

Das Programm sucht in allen geladenen AASX-Dateien nach einem Submodel namens machine_state und iteriert über alle Properties in diesem Submodell. Wenn OPC UA einen Wert für die Eigenschaft zurückgibt, wird dieser aktualisiert, andernfalls wird die Property übersprungen.

Um die Performance für größere Submodels zu verbessern, sollte der neue Python OPC UA-Client verwendet werden, der asynchrone Anfragen unterstützt und somit die Eigenschaftenwerte gleichzeitig aktualisieren kann, was die Iterationszeit drastisch reduziert.

# Installing and Running:

First, create a venv and install the required libraries as specified in `requirements.txt`, then activate the venv. To avoid outdated instructions, please google how to do that.
Then simply adjust the CouchDB credentials, `.aasx` file names and the OPC UA connection string in `src/live-data-couchdb.py` and run it (*in the venv!*).