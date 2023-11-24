import configparser
import logging
from multiprocessing import Event
from queue import Queue
from threading import Thread
import time
import serial
from aretas_packet import AretasPacket


class BasicSerialParams:
    def __init__(self, port="/dev/ttyUSB0", baud_rate=115200, mac=None):
        self._port = port
        self._baud_rate = baud_rate
        self._self_mac = mac

    def get_baud_rate(self) -> int:
        return self._baud_rate

    def get_port(self) -> str:
        return self._port

    def get_mac(self)-> int or None:
        return self._self_mac


class SerialPortReadWriter(Thread):
    """
    This thread monitors the serial port specified in the cfg
    and injects bytes and/or payloads into the semaphore queue
    """

    def __init__(self, payload_queue: Queue, sig_event: Event, serial_params: BasicSerialParams):
        super(SerialPortReadWriter, self).__init__()
        self.logger = logging.getLogger(__name__)

        self.pause_reading = False
        # read in the global app config
        config = configparser.ConfigParser()
        config.read('config.cfg')

        self.thread_sleep = config.getboolean('DEFAULT', 'thread_sleep')
        self.thread_sleep_time = config.getfloat('DEFAULT', 'thread_sleep_time')

        self.payload_queue = payload_queue

        self.com_id = serial_params.get_port()

        # enumerate and open the port
        self.ser = serial.Serial()
        self.ser.port = serial_params.get_port()
        self.ser.baudrate = serial_params.get_baud_rate()
        self.ser.parity = serial.PARITY_NONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = 1
        self.ser.open()

        self.sig_event = sig_event

        self.attempted_decodes = 0
        self.packet_count = 0

        self.self_mac = serial_params.get_mac()

    def run(self):
        # enqueue bytes into the self.message_queue
        while True:
            if self.sig_event.is_set():
                self.logger.info("{0} Exiting {1}".format(self.com_id, self.__class__.__name__))
                break

            if not self.pause_reading:

                self.read_port()
                # sleep after for a while

                if self.thread_sleep is True:
                    time.sleep(self.thread_sleep_time)

            else:

                time.sleep(0.01)  # sleep for 10ms and allow UART to "settle"

    def write_cmd(self, cmd: bytes):
        """
        The idea is that if someone calls this function on the class, we "pause" the read loop in the class run()
        so we avoid port conflicts, emit the data over the serial port then return control to the read loop

        @param cmd:
        @return:
        """
        self.pause_reading = True
        # write data to the port
        self.ser.write(cmd)
        self.pause_reading = False
        pass

    def read_port(self):
        """
        In this instance, we're reading the ultra simple Aretas packet format
        it's just a comma delimited string terminated by \n
        the format is
        mac, type, data\n

        @return:
        """
        buffer = bytearray()
        done = False
        while not done:
            it = self.ser.read(1)
            if it.decode() == '\n':
                done = True
                self.attempted_decodes += 1
                packet = bytes(buffer)
                buffer.clear()
                payload = AretasPacket.parse_packet(packet, self.self_mac)

                if payload is not None:
                    self.payload_queue.put(payload)
                    self.packet_count += 1
                    if self.packet_count % 200 == 0:
                        self.logger.info("{0}: Valid packet count = {1} attempted decodes = {2}"
                                         .format(self.com_id, self.packet_count, self.attempted_decodes))
            else:
                for b in it:
                    buffer.append(b)
