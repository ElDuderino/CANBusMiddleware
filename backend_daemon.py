from threading import Event
from queue import Queue
import configparser
import logging
from logging.handlers import RotatingFileHandler
from message_harvester import MessageHarvester
from packet_mocker import SerialPortMocker
from serial_port_read_writer import SerialPortReadWriter, BasicSerialParams

# An example of using logging.basicConfig rather than logging.fileHandler()
logging.basicConfig(level=logging.INFO,
                    handlers=[
                        RotatingFileHandler("CANBusMiddleware.log", maxBytes=50000000, backupCount=5)
                    ],
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def parse_serial_params(serial_params_str: str, baud_rate: int) -> list[BasicSerialParams]:
    ret = list()

    params_pairs = serial_params_str.split('|')
    for param_pair_str in params_pairs:
        param_pair = param_pair_str.split(',')
        str_port = param_pair[0]
        mac = int(param_pair[1])
        ret.append(BasicSerialParams(str_port, baud_rate, mac))

    return ret


def main():
    import signal
    import sys

    # read in the global app config
    config = configparser.ConfigParser()
    config.read('config.cfg')

    serial_params_str = config.get("SERIAL", "serial_ports", fallback="")
    serial_params_baud_rate = config.getint("SERIAL", "baud_rate", fallback=115200)

    serial_port_configs = parse_serial_params(serial_params_str, serial_params_baud_rate)

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

    serial_port_threads = list()

    for serial_config in serial_port_configs:
        logger.info("Serial port monitor {} thread starting:".format(serial_config.get_port()))
        serial_port_thread = SerialPortReadWriter(mq_payload_queue,
                                                  thread_sig_event,
                                                  serial_config)
        serial_port_thread.start()
        serial_port_threads.append(serial_port_thread)
        logger.info("Serial port monitor {} thread started.".format(serial_config.get_port()))

    logger.info("Message harvester thread starting:")
    message_harvester_thread = MessageHarvester(mq_payload_queue,
                                                thread_sig_event)
    message_harvester_thread.start()
    logger.info("Message harvester thread started.")

    if config.getboolean("DEBUG_SERIAL", 'packet_mocker_enable'):
        logger.info("Starting Serial Port Mocker:")
        serial_port_mocker = SerialPortMocker(thread_sig_event)
        serial_port_mocker.start()
        logger.info("Serial Port Mocker started.")

    # Test setting the termination event
    # print("Setting thread_sig_event")
    # thread_sig_event.set()

    for t in serial_port_threads:
        t.join()

    message_harvester_thread.join()

    if config.getboolean("DEBUG_SERIAL", 'packet_mocker_enable'):
        serial_port_mocker.join()


if __name__ == "__main__":
    main()
