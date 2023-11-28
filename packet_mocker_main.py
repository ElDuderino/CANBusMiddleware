import configparser
import logging
from time import time
from logging.handlers import RotatingFileHandler
from multiprocessing import Event

from packet_mocker import SerialPortMocker

# An example of using logging.basicConfig rather than logging.fileHandler()
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


def main():
    # this is a shared event handler among all the threads
    thread_sig_event = Event()

    # read in the global app config
    config = configparser.ConfigParser()
    config.read('config.cfg')

    serial_ports = config.get("DEBUG_SERIAL", "serial_ports", fallback=None).split(',')
    baud_rate = config.getint("DEBUG_SERIAL", "baud_rate", fallback=115200)

    serial_port_mockers = list()

    for serial_port in serial_ports:
        logger.info("Starting Serial Port Mocker on {}:".format(serial_port))
        serial_port_mocker = SerialPortMocker(serial_port, baud_rate, thread_sig_event)
        serial_port_mocker.start()
        logger.info("Serial Port Mocker started.")
        serial_port_mockers.append(serial_port_mocker)

    for serial_port_mocker in serial_port_mockers:
        serial_port_mocker.join(1000)


if __name__ == "__main__":
    main()
