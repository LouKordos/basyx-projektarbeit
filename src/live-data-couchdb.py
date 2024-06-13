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


# To support quitting with CTRL + C
exit_flag = False
def signal_handler(signal, frame):
    print("CTRL+C detected, setting exit flag.")
    global exit_flag
    exit_flag = True
signal.signal(signal.SIGINT, signal_handler)

# ADJUST HERE
couchdb_url = "http://localhost:5984"
couchdb_database = "basyx-test-db"
couchdb_user = "admin"
couchdb_password = "admin"

basyx.aas.backend.couchdb.register_credentials(couchdb_url, couchdb_user, couchdb_password)

# Now, we create a CouchDBObjectStore as an interface for managing the objects in the CouchDB server.
couchdb_object_store = basyx.aas.backend.couchdb.CouchDBObjectStore(couchdb_url, couchdb_database)
# For reading auxiliary files, should not be needed in this case
file_store = aasx.DictSupplementaryFileContainer()

# This might need to be adjusted if you use other AASX files
machine_names = ["machine1_speiser","machine2_krempel","machine3_leger"]

# Read all contained AAS objects and all referenced auxiliary files
# This should be a loop, not changing it because I can't test it remotely
with aasx.AASXReader(f"../{machine_names[0]}.aasx") as reader:
    reader.read_into(object_store=couchdb_object_store,
                     file_store=file_store)
    
with aasx.AASXReader(f"../{machine_names[1]}.aasx") as reader:
    reader.read_into(object_store=couchdb_object_store,
                        file_store=file_store)
    
with aasx.AASXReader(f"../{machine_names[2]}.aasx") as reader:
    reader.read_into(object_store=couchdb_object_store,
                        file_store=file_store)

# Used for updating all properties defined in a submodel
def get_all_submodel_properties(submodel: model.Submodel) -> List[model.Property]:
    return [submodel_element for submodel_element in walk_submodel(submodel) if isinstance(submodel_element, model.Property)]

# This simply converts "machine1_speiser" into "Speiser" because the OPC UA Server at the assembly line follows this naming scheme.
def get_opc_ua_machine_name(name):
    return name.split("_")[1].title()

# ADJUST HERE
client = Client("opc.tcp://localhost:49580/")
# client = Client("opc.tcp://admin@localhost:4840/freeopcua/server/") #connect using a user
client.connect()
# Client has a few methods to get proxy to UA nodes that should always be in address space such as Root or Objects
root = client.get_root_node()

# Set a property value, and update to be safe.
def set_submodel_property_value(submodel_id, property_name, value):
    machine_state_submodel = couchdb_object_store.get_identifiable(submodel_id)
    machine_state_submodel.update()
    machine_state_submodel.get_referable(property_name).value = float(value)
    machine_state_submodel.get_referable(property_name).commit()
    machine_state_submodel.update()

# Get a property value
def get_submodel_property_value(submodel_id, property_name):
    machine_state_submodel = couchdb_object_store.get_identifiable(submodel_id)
    machine_state_submodel.update()
    return machine_state_submodel.get_referable(property_name).value

# Fetch actual OPC UA value from assembly line OPC UA server.
# The string array in get_child is the path to the value, this most likely needs to be adjusted depending on the server.
def get_opc_ua_property_value(machine_name, property_name):
    try:
        return root.get_child(["0:Objects", "0:Prozess", f"0:{machine_name}", f"0:{property_name}"]).get_value()
    except Exception as e:
        print(f"Error occured while trying to get {property_name} value from machine_name={machine_name} from OPC UA server, skipping:", e)
        return None
# Adjust this based on required performance. Note that depending on the client running this script and the OPC UA server performance,
# the performance might be quite bad. For example, the assembly line with ~20 property values per loop iteration takes 600-800ms.
# If you want to update many more, take a look at https://github.com/FreeOpcUa/opcua-asyncio and rewrite the loop accordingly
# to fetch the value and use a callback for each update.
LOOP_FREQUENCY = 1 # Hz

# checks for exit flag
while not exit_flag:
    before = time.time()
    try:
        # Read data from OPC UA, write it to the CouchDB Submodel Object store and commit the changes.
        for machine_name in machine_names:
            for property in get_all_submodel_properties(couchdb_object_store.get_identifiable(f"https://ita.rwth-aachen.de/{machine_name}/machine_state")):
                opc_ua_value = get_opc_ua_property_value(machine_name=get_opc_ua_machine_name(machine_name), property_name=property.id_short)
                print(f"machine_name={machine_name}, property_name={property.id_short}, value={opc_ua_value}")
                if opc_ua_value != None:
                    set_submodel_property_value(submodel_id=f"https://ita.rwth-aachen.de/{machine_name}/machine_state", property_name=property.id_short, value=opc_ua_value)
                    # print(get_submodel_property_value(submodel_id=f"https://ita.rwth-aachen.de/{machine_name}/machine_state", property_name=property.id_short))

    except Exception as e:
        print("Exception caught in main loop, exiting:", e.format_exc())
        exit_flag = True

    after = time.time()
    print(f"Iteration time: {(after - before)*1000.0}ms")
    time.sleep(max(0, 1/LOOP_FREQUENCY - (after - before))) # Make loop run at roughly LOOP_FREQUENCY

client.disconnect()