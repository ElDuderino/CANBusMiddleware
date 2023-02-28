from threading import Event
from queue import Queue
import configparser
import logging
from message_harvester import MessageHarvester
from packet_mocker import SerialPortMocker
from serial_port_read_writer import SerialPortReadWriter

# An example of using logging.basicConfig rather than logging.fileHandler()
logging.basicConfig(filename="CANBusMiddleware.log",
                    filemode="a",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    import signal
    import sys

    # read in the global app config
    config = configparser.ConfigParser()
    config.read('config.cfg')

    # this is a shared event handler among all the threads
    thread_sig_event = Event()

    def signal_handler(sig, frame):
        print('You pressed Ctrl+C!')
        thread_sig_event.set()
        sys.exit(0)


    # define the signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    # this is the shared message queue for the serial port and message harvester threads
    mq_payload_queue: Queue = Queue()

    logger.info("Serial port monitor thread starting:")
    serial_port_thread = SerialPortReadWriter(mq_payload_queue,
                                              thread_sig_event)
    serial_port_thread.start()
    logger.info("Serial port monitor thread started.")

    logger.info("Message harvester thread starting:")
    message_harvester_thread = MessageHarvester(mq_payload_queue,
                                                thread_sig_event)
    message_harvester_thread.start()
    logger.info("Message harvester thread started.")

    grpc_server_thread = None

    if config.getboolean("DEBUG_SERIAL", 'packet_mocker_enable'):
        logger.info("Starting Serial Port Mocker:")
        serial_port_mocker = SerialPortMocker(thread_sig_event)
        serial_port_mocker.start()
        logger.info("Serial Port Mocker started.")

    # Test setting the termination event
    # print("Setting thread_sig_event")
    # thread_sig_event.set()

    serial_port_thread.join()
    message_harvester_thread.join()

    if config.getboolean("DEBUG_SERIAL", 'packet_mocker_enable'):
        serial_port_mocker.join()
