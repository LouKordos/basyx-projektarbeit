#!/usr/bin/env python3
import time
import sys
import signal
import basyx.aas.examples.data.example_aas
import basyx.aas.backend.couchdb
from basyx.aas import model
from basyx.aas.adapter import aasx
import basyx.aas.model
import basyx.aas.util.identification
from basyx.aas.util.traversal import walk_submodel
import basyx.aas.util
from typing import List

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

machine_names = ["machine1_speiser","machine2_krempel","machine3_leger"]

with aasx.AASXReader(f"../{machine_names[0]}.aasx") as reader:
    # Read all contained AAS objects and all referenced auxiliary files
    reader.read_into(object_store=couchdb_object_store,
                     file_store=file_store)
    
with aasx.AASXReader(f"../{machine_names[1]}.aasx") as reader:
    # Read all contained AAS objects and all referenced auxiliary files
    reader.read_into(object_store=couchdb_object_store,
                        file_store=file_store)
    
with aasx.AASXReader(f"../{machine_names[2]}.aasx") as reader:
    # Read all contained AAS objects and all referenced auxiliary files
    reader.read_into(object_store=couchdb_object_store,
                        file_store=file_store)

def get_all_submodel_properties(submodel: model.Submodel) -> List[model.Property]:
    return [submodel_element for submodel_element in walk_submodel(submodel) if isinstance(submodel_element, model.Property)]

client = Client("opc.tcp://localhost:4840/freeopcua/server/")
# client = Client("opc.tcp://admin@localhost:4840/freeopcua/server/") #connect using a user
client.connect()
# Client has a few methods to get proxy to UA nodes that should always be in address space such as Root or Objects
root = client.get_root_node()
print("Objects node of OPCUA is: ", root)
# Node objects have methods to read and write node attributes as well as browse or populate address space
print("Children of OPCUA root are: ", root.get_children())

def set_submodel_property_value(submodel_id, property_name, value):
    machine_state_submodel = couchdb_object_store.get_identifiable(submodel_id)
    machine_state_submodel.update()
    machine_state_submodel.get_referable(property_name).value = value
    machine_state_submodel.get_referable(property_name).commit()
    machine_state_submodel.update()

def get_submodel_property_value(submodel_id, property_name):
    machine_state_submodel = couchdb_object_store.get_identifiable(submodel_id)
    machine_state_submodel.update()
    return machine_state_submodel.get_referable(property_name).value

def get_opc_ua_property_value(property_name):
    try:
        return root.get_child(["0:Objects", "2:machine1", f"2:{property.id_short}"]).get_value()
    except Exception as e:
        print(f"Error occured while trying to get {property_name} value from OPC UA server, skipping:", e)
        return None
    
LOOP_FREQUENCY = 10 # Hz

while not exit_flag:
    before = time.time()
    try:
        # Read data from OPC UA, write it to the CouchDB Submodel Object store and commit the changes.
        # TODO: One class for each machine, standardized to avoid rewriting code, write pseudocode first to plan
        # TODO: Implement logger and replace all print statements

        for machine_name in machine_names:
            for property in get_all_submodel_properties(couchdb_object_store.get_identifiable(f"https://ita.rwth-aachen.de/{machine_name}/machine_state")):
                opc_ua_value = get_opc_ua_property_value(property_name=property.id_short)
                if opc_ua_value != None:
                    set_submodel_property_value(submodel_id=f"https://ita.rwth-aachen.de/{machine_name}/machine_state", property_name=property.id_short, value=opc_ua_value)
                    # print(get_submodel_property_value(submodel_id=f"https://ita.rwth-aachen.de/{machine_name}/machine_state", property_name=property.id_short))

    except Exception as e:
        print("Exception caught in main loop, exiting:", e)
        exit_flag = True

    after = time.time()
    print(f"Iteration time: {(after - before)*1000.0}ms")
    time.sleep(max(0, 1/LOOP_FREQUENCY - (after - before))) # Make loop run at roughly LOOP_FREQUENCY


client.disconnect()