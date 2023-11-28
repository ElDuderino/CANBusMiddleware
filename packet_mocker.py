import configparser
import logging
from multiprocessing import Event
from threading import Thread
from AretasPythonAPI.utils import Utils as AretasUtils
import serial
import time
import random
import math
import numpy as np
from ev_battery_sensor_types import EVBatterySensorTypes


class TempMocker:
    """
    For the temperature mocking, we just use a sin function
    scaled to work with the ordinal hour value (since epoch)

    something like:

    2sin(0.04x+a)+b + noise

    where a is a random integer between 0-10 to shift the output left/right
    so that multiple channels don't overlap and

    b is the "center" temperature

    rng is just the span above / below the center

    You'll want to spin up one mocker per channel so they have different outputs
    """

    def __init__(self, rng: float = 2.0):
        self.a = random.randint(1, 10) * 1.0
        self.b = 25.0
        self.rng = rng

    def get_y(self, x) -> float:
        noise = random.gauss() / 10.0
        y = self.rng * math.sin(0.04 * x + self.a) + self.b + noise
        return y

    def get_temp_hr(self):
        """
        Use this method to get a simulated temp for the current time
        """
        now = AretasUtils.now_ms()

        one_hour_ms = 60 * 60 * 1000
        # the current ordinal hour value since epoch
        current_hour_f = float(now) / float(one_hour_ms)

        return self.get_y(current_hour_f)


class CellMocker:

    def __init__(self, min_max_range: tuple = (3.0, 4.3),
                 frequency_ms: int = 1 * 60 * 60 * 1000 / 2,
                 time_range_ms=4 * 60 * 60 * 1000):

        """
        Mock a triangle wave function over time for a voltage range / period
        All time related params are milliseconds and/or milliseconds from epoch
        the default params simulate a voltage rising and falling from 3.0 to 4.3
        over a period of one hour - note that this isn't a wave in a sinusoidal sense
        the frequency is the rise/fall time

        :param min_max_range:
        :param frequency_ms: how often does the value go through a cycle
        :param time_range_ms: over what time range do we want to create the static buffer of values
        """

        self.interval = 10000  # every 10 seconds
        n_values = int(time_range_ms / self.interval)

        x_values = np.linspace(0, time_range_ms, n_values)  # x values in milliseconds

        self.voltage_values = CellMocker.triangle_wave_n(x_values, min_max_range, frequency_ms)

        self.last_call = None
        self.ys_index = 0

    @staticmethod
    def triangle_wave_n(x, min_max_range, period):
        min_val, max_val = min_max_range
        amplitude = max_val - min_val

        y = (amplitude / period) * (period - np.abs(x % (2 * period) - period)) + min_val

        return y

    def get_next_value(self, now=None):

        if now is None:
            now = AretasUtils.now_ms()

        if self.last_call is not None:
            t_diff = now - self.last_call

            next_increment = int(t_diff / self.interval)  # how many steps do we need to take

            if self.ys_index + next_increment < len(self.voltage_values):
                self.ys_index += next_increment

            if self.ys_index + next_increment > len(self.voltage_values):
                self.ys_index = (self.ys_index + next_increment) - len(self.voltage_values)

            if self.ys_index + next_increment == len(self.voltage_values):
                self.ys_index = 0

            value = self.voltage_values[self.ys_index]

        else:
            value = self.voltage_values[self.ys_index]

        self.last_call = now

        noise = random.gauss() / 10.0
        return value + noise


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

        self.mac = 0

        self.temp_mocker1 = TempMocker()
        self.temp_mocker2 = TempMocker()
        self.temp_mocker3 = TempMocker()
        self.temp_mocker4 = TempMocker()

        self.voltage_mocker1 = CellMocker()
        self.voltage_mocker2 = CellMocker((288.0, 403.0))

        self.flag_send = False

        self.packets_to_write = list()

    @staticmethod
    def create_uart_packet(mac: int, payload_type: int, data: float or str) -> dict:
        """
        create a string packet to write over the uart
        """
        payload = "{0},{1},{2}\n".format(mac, payload_type, data)

        return payload

    def create_cell_payload(self, now_ms: int) -> str:

        voltage = self.voltage_mocker1.get_next_value(now_ms)

        ret = ""
        for i in range(96):
            if i == 95:
                ret = ret + str(voltage)
            else:
                ret = ret + str(voltage) + "|"

        return ret

    def get_next_packet(self):
        """
        Get the next packet based on the type
        We should extend each of these functions to include realistic simulated data
        """
        packet_type = self.supported_packets[self.packet_index]
        payload = None
        now_ms = AretasUtils.now_ms()

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

            data = self.temp_mocker1.get_temp_hr()
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_TEMP_2.value:

            data = self.temp_mocker2.get_temp_hr()
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_TEMP_3.value:

            data = self.temp_mocker3.get_temp_hr()
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_TEMP_4.value:

            data = self.temp_mocker4.get_temp_hr()
            payload = self.create_uart_packet(self.mac, packet_type, data)

        elif packet_type == EVBatterySensorTypes.EV_BAT_CELL_VOLTAGES.value:

            data = self.create_cell_payload(now_ms)
            payload = self.create_uart_packet(self.mac, packet_type, data)

        self.increment_type()
        return payload

    def increment_type(self):

        self.packet_index += 1
        if not (self.packet_index < len(self.supported_packets)):
            self.packet_index = 0
            self.flag_send = True


class SerialPortMocker(Thread):
    """
    Use this to write protobuf mock data to the com0com serial port
    """

    def __init__(self, serial_port, baud_rate, sig_event: Event):
        super(SerialPortMocker, self).__init__()

        # read in the global app config
        config = configparser.ConfigParser()
        config.read('config.cfg')
        self.logger = logging.getLogger(__name__)

        self.packet_mocker = PacketMocker()

        self.serial_port = serial_port
        self.baud_rate = baud_rate

        self.ser = serial.Serial()
        self.ser.port = self.serial_port
        self.ser.baudrate = self.baud_rate
        self.ser.parity = serial.PARITY_NONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = 1
        self.ser.open()

        self.sig_event = sig_event

        # set the current time in milliseconds
        self.last_run_time = AretasUtils.now_ms()
        self.n_packets = 0
        self.packet_mocker_interval_ms = config.getint('DEBUG_SERIAL', 'packet_mocker_interval_ms')

    def run(self):
        self.logger.info("Starting serial port mocker")
        while True:
            now = AretasUtils.now_ms()
            if now - self.last_run_time > self.packet_mocker_interval_ms:  # run every n milliseconds
                # write a packet to the port
                self.last_run_time = now
                self.dump_packets()

            if self.sig_event.is_set():
                self.logger.info("Exiting {}".format(self.__class__.__name__))
                break

            time.sleep((self.packet_mocker_interval_ms / 1000.0) / 10.0)  # sleep for some fraction of the wait time

    def dump_packets(self):
        while self.write_packet() is False:
            pass
        for packet in self.packet_mocker.packets_to_write:
            self.ser.write(str.encode(packet))

        self.packet_mocker.packets_to_write.clear()

    def write_packet(self):
        """
        We write the next packet to the UART
        Keep in mind that depending on the switch statements in the mocker, we may not get a
        valid packet for every iteration (since we don't have 100% coverage of the enum in the switch statements)
        """
        packet = self.packet_mocker.get_next_packet()
        if packet is None:
            return False

        self.logger.info("{} Writing mock packet {}".format(self.serial_port, self.n_packets))
        self.logger.info("Packet: {}".format(packet))
        self.n_packets += 1
        self.packet_mocker.packets_to_write.append(packet)

        if self.packet_mocker.flag_send is True:
            packet = self.packet_mocker.create_uart_packet(0, 0, 0)
            self.packet_mocker.packets_to_write.append(packet)
            self.packet_mocker.flag_send = False
            return True

        return False
