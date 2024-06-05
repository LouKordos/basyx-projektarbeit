import sys
sys.path.insert(0, "..")
import time
from opcua import ua, Server

if __name__ == "__main__":

    # Setup server
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")

    # setup our own namespace, not really necessary but required by spec
    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)

    # get Objects node, this is where we should put our nodes
    objects = server.get_objects_node()

    # populating address space
    machine1 = objects.add_object(idx, "machine1")
    quetschwalze_1_drehzahl = machine1.add_variable(idx, "quetschwalze_1_drehzahl_m_min", 6.7)
    quetschwalze_1_drehzahl.set_writable() # Set MyVariable to be writable by clients

    server.start()
    
    try:
        count = 0
        while True:
            time.sleep(0.1)
            count += 0.1
            quetschwalze_1_drehzahl.set_value(count)
    finally:
        #close connection, remove subcsriptions, etc
        server.stop()