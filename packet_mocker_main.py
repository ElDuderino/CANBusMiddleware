import configparser
import logging
import time
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

    logger.info("Starting Serial Port Mocker:")
    serial_port_mocker = SerialPortMocker(thread_sig_event)
    serial_port_mocker.start()
    logger.info("Serial Port Mocker started.")

    while serial_port_mocker.is_alive():
        time.sleep(0.1)

    serial_port_mocker.join()


if __name__ == "__main__":
    main()
