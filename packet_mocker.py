import configparser
import logging
from multiprocessing import Event
from threading import Thread
from AretasPythonAPI.utils import Utils as AretasUtils
import serial
from time import time

from ev_battery_sensor_types import EVBatterySensorTypes


class PacketMocker:
    """
    This class just steps through the various types and if we have a match in our
    get_next_packet selection criteria, we generate a simulated packet
    Right now we don't support every typem, just a subset for simulation
    """
    def __init__(self):
        self.packet_index = 0
        # list of types by value (integer)
        self.supported_packets = [i.value for i in EVBatterySensorTypes]

        # read in the global app config
        config = configparser.ConfigParser()
        config.read('config.cfg')

        # determine if we are reading byte by byte or not (prefer not)
        self.mac = config.getint('DEFAULT', 'self_mac')

    @staticmethod
    def create_uart_packet(mac: int, payload_type: int, data: float) -> dict:
        """
        create a string packet to write over the uart
        """
        payload = "{0},{1},{2}\n".format(mac, payload_type, data)

        return payload

    def get_next_packet(self):
        """
        Get the next packet based on the type
        We should extend each of these functions to include realistic simulated data
        """
        packet_type = self.supported_packets[self.packet_index]
        payload = None

        if packet_type == EVBatterySensorTypes.EV_BAT_HX.value:

            data = 98.0
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_AHR.value:

            data = 97
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_HV_BAT_CURRENT_1.value:

            data = 10.0
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_HV_BAT_VOLTAGE.value:

            data = 390.0
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_SOH.value:

            data = 89.34
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_SOC.value:

            data = 95.0
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_TEMP_1.value:

            data = 23.2
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_TEMP_2.value:

            data = 22.1
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_TEMP_3.value:

            data = 30.0
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_TEMP_4.value:

            data = 22.0
            payload = self.create_uart_packet(self.mac, packet_type, data)

        self.increment_type()
        return payload

    def increment_type(self):

        self.packet_index += 1
        if self.packet_index < len(self.supported_packets):
            pass
        else:
            self.packet_index = 0


class SerialPortMocker(Thread):
    """
    Use this to write protobuf mock data to the com0com serial port
    """

    def __init__(self, sig_event: Event):
        super(SerialPortMocker, self).__init__()

        # read in the global app config
        config = configparser.ConfigParser()
        config.read('config.cfg')
        self.logger = logging.getLogger(__name__)

        self.packet_mocker = PacketMocker()

        self.serial_port = config['DEBUG_SERIAL']['serial_port']
        self.baud_rate = config['DEBUG_SERIAL']['baud_rate']

        self.ser = serial.Serial()
        self.ser.port = self.serial_port
        self.ser.baudrate = self.baud_rate
        self.ser.parity = serial.PARITY_NONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = 1
        self.ser.open()

        self.sig_event = sig_event

        # set the current time in milliseconds
        self.last_run_time = int(time() * 1000)
        self.n_packets = 0
        self.packet_mocker_interval_ms = config.getint('DEBUG_SERIAL', 'packet_mocker_interval_ms')
        pass

    def run(self):
        while True:
            now = int(time() * 1000)
            if now - self.last_run_time > self.packet_mocker_interval_ms:  # run every n milliseconds
                # write a packet to the port
                self.last_run_time = now
                self.write_packet()

            if self.sig_event.is_set():
                self.logger.info("Exiting {}".format(self.__class__.__name__))
                break
            pass

    def write_packet(self):
        """
        We write the next packet to the UART
        Keep in mind that depending on the switch statements in the mocker, we may not get a
        valid packet for every iteration (since we don't have 100% coverage of the enum in the switch statements)
        """
        packet = self.packet_mocker.get_next_packet()
        if packet is None:
            return
        self.logger.info("Writing mock packet {}".format(self.n_packets))
        self.logger.info("Packet: {}".format(packet))
        self.n_packets += 1
        self.ser.write(str.encode(packet))

