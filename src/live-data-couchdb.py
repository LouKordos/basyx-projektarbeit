#!/usr/bin/env python3
import time
import sys
import signal
import basyx.aas.examples.data.example_aas
import basyx.aas.backend.couchdb
from basyx.aas import model
from basyx.aas.adapter import aasx

# needed for OPC UA client
sys.path.insert(0, "..")
from opcua.ua.uaerrors import _auto
from opcua import Client

exit_flag = False

def signal_handler(signal, frame):
    print("CTRL+C detected, setting exit flag.")
    global exit_flag
    exit_flag = True

signal.signal(signal.SIGINT, signal_handler)

couchdb_url = "http://localhost:5984"
couchdb_database = "basyx-test-db"
couchdb_user = "admin"
couchdb_password = "iNMkk3idV5fHPmoKycEsoZ84zHjYQftXxhqW6qbBYdCJ2GFg7pYZm4MMdbHg"

# Provide the login credentials to the CouchDB backend.
# These credentials are used whenever communication with this CouchDB server is required either via the
# CouchDBObjectStore or via the update()/commit() backend.
basyx.aas.backend.couchdb.register_credentials(couchdb_url, couchdb_user, couchdb_password)

# Now, we create a CouchDBObjectStore as an interface for managing the objects in the CouchDB server.
couchdb_object_store = basyx.aas.backend.couchdb.CouchDBObjectStore(couchdb_url, couchdb_database)

# For reading auxiliary files, should not be needed in this case
file_store = aasx.DictSupplementaryFileContainer()

with aasx.AASXReader("../machine1.aasx") as reader:
    # Read all contained AAS objects and all referenced auxiliary files
    reader.read_into(object_store=couchdb_object_store,
                     file_store=file_store)

machine_state_submodel_reference = model.ModelReference(
    (model.Key(
        type_=model.KeyTypes.SUBMODEL,
        value='https://ita.rwth-aachen.de/machine-state-submodel'),
    ),
    type_=model.Submodel
)

machine_state_submodel = machine_state_submodel_reference.resolve(couchdb_object_store)
print(machine_state_submodel.get_referable("quetschwalze_1_drehzahl_m_min").)

property_reference = model.ModelReference(
           (model.Key(
                type_=model.KeyTypes.SUBMODEL,
                value='https://ita.rwth-aachen.de/machine-state-submodel'),
            model.Key(
                type_=model.KeyTypes.PROPERTY,
                value='quetschwalze_1_drehzahl_m_min'),
            ),
            type_=model.Property
        )

quetschwalze_1_drehzahl_couchdb = property_reference.resolve(couchdb_object_store)
print(quetschwalze_1_drehzahl_couchdb.value)

client = Client("opc.tcp://localhost:4840/freeopcua/server/")
# client = Client("opc.tcp://admin@localhost:4840/freeopcua/server/") #connect using a user
client.connect()

# Client has a few methods to get proxy to UA nodes that should always be in address space such as Root or Objects
root = client.get_root_node()
print("Objects node is: ", root)
# Node objects have methods to read and write node attributes as well as browse or populate address space
print("Children of root are: ", root.get_children())

while not exit_flag:
    # Read data from OPC UA, write it to the CouchDB Submodel Object store and commit the changes.
    before = time.time()

    try:
        # TODO: Consider renaming properties in submodel to the same as OPC UA server so that all properties can be iterated over and fetched without manually specifying them all
        # TODO: Put this into separate functions
        opc_ua_property_name = "quetschwalze_1_drehzddahl"
        opc_ua_property_value = root.get_child(["0:Objects", "2:machine1", f"2:{opc_ua_property_name}"]).get_value()
        print(f"{opc_ua_property_name} value is:", opc_ua_property_value)

        quetschwalze_1_drehzahl_couchdb.value = opc_ua_property_value
        quetschwalze_1_drehzahl_couchdb.commit()
    except _auto.BadNoMatch as e:
        print(f"Property={opc_ua_property_name} was not found on OPC UA server, skipping:", e)
    except Exception as e:
        print("Exception caught, exiting:", e)
        exit_flag = True

    after = time.time()
    print(f"Iteration time: {(after - before)*1000.0}ms")
    time.sleep(max(0, 0.1 - (after - before))) # Make loop run at roughly 100Hz

client.disconnect()