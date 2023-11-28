import configparser
import logging
from multiprocessing import Queue, Event
from threading import Thread
import time
import serial
from aretas_packet import AretasPacket


class ReadLine:
    """
    A 5-10x improvement over pyserial readline
    """
    def __init__(self, ser):
        self.buf = bytearray()
        self.ser = ser

    def readline(self):
        """
        Read in a line of data from the serial port ending in \n
        :return:
        """
        i = self.buf.find(b"\n")
        if i >= 0:
            r = self.buf[:i + 1]
            self.buf = self.buf[i + 1:]
            return r
        while True:
            # if the buffer has > 2048 bytes, read 2048 bytes
            # if the buffer has < 2048 bytes, read what's in the buffer
            # if the buffer has 0 bytes, read at least 1 byte
            i = max(1, min(2048, self.ser.in_waiting))
            data = self.ser.read(i)
            i = data.find(b"\n")
            if i >= 0:
                r = self.buf + data[:i + 1]
                self.buf[0:] = data[i + 1:]
                return r
            else:
                self.buf.extend(data)


class BasicSerialParams:
    def __init__(self, port="/dev/ttyUSB0", baud_rate=115200, mac=None):
        self._port = port
        self._baud_rate = baud_rate
        self._self_mac = mac

    def get_baud_rate(self) -> int:
        return self._baud_rate

    def get_port(self) -> str:
        return self._port

    def get_mac(self) -> int or None:
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

        print("Initializing serial port:{}".format(serial_params.get_port()))

        # enumerate and open the port
        self.ser = serial.Serial(timeout=None)
        self.ser.port = serial_params.get_port()
        self.ser.baudrate = serial_params.get_baud_rate()
        self.ser.parity = serial.PARITY_NONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = 1
        self.ser.open()

        print("Baud rate:{}".format(self.ser.baudrate))

        print("Opened serial port:{}".format(serial_params.get_port()))

        self.sig_event = sig_event

        self.attempted_decodes = 0
        self.packet_count = 0

        self.self_mac = serial_params.get_mac()

        self.latest_data: dict[int, dict] = dict()

        self.aretas_packet_decoder = AretasPacket()

        self.line_reader = ReadLine(self.ser)

    def run(self):
        last_ran_time = 0

        # enqueue bytes into the self.message_queue
        while True:

            now = int(time.time() / 1000)

            if self.sig_event.is_set():
                self.logger.info("{0} Exiting {1}".format(self.com_id, self.__class__.__name__))
                break

            if self.pause_reading is False:

                print("Reading port")
                n_bytes_read = self.read_packet()
                print("Done reading port")
                print("Time taken:{}ms bytes read:{}".format((now - last_ran_time), n_bytes_read))
                last_ran_time = now

            else:
                if self.thread_sleep is True:
                    time.sleep(self.thread_sleep_time)

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

    def flush_packets(self):
        """
        We have received the "flush packet command" at the end
        of a stream of packets from a CANBed board, send them
        on for processing
        :return:
        """
        packets = list()
        for sensor_type, packet in self.latest_data.items():
            packets.append(packet)

        self.payload_queue.put(packets)

        self.latest_data.clear()

    def queue_packet(self, packet: dict):
        """
        Queue packets until the flush packet command is received
        :param packet:
        :return:
        """
        if int(packet['type']) == 0:
            print("Flushing packets")
            self.flush_packets()
        else:
            print(packet)
            self.latest_data[packet['type']] = packet

    def read_packet(self):
        """
        In this instance, we're reading the ultra simple Aretas packet format
        it's just a comma delimited string terminated by \n
        the format is
        mac, type, data\n

        @return:
        """
        buffer = bytes()
        done = False
        while not done:

            buffer = self.line_reader.readline()
            done = True
            self.attempted_decodes += 1

            payload = self.aretas_packet_decoder.parse_packet(buffer, self.self_mac)

            if payload is not None:
                self.queue_packet(payload)
                self.packet_count += 1
                if self.packet_count % 200 == 0:
                    self.logger.info("{0}: Valid packet count = {1} attempted decodes = {2}"
                                     .format(self.com_id, self.packet_count, self.attempted_decodes))

            return len(buffer)
