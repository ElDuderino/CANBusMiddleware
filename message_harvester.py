import configparser
import logging
import time
from multiprocessing import Queue, Event
from threading import Thread
import numpy as np

from api_message_writer import APIMessageWriter
from redis_message_processor import RedisQueueReader
from sensor_message_item import SensorMessageItem
from ev_battery_sensor_types import EVBatterySensorTypes
from AretasPythonAPI.utils import Utils as AretasUtils


class StatsQueueItem:
    def __init__(self, timestamp: int, n_items: int):
        self.timestamp = timestamp
        self.n_items = n_items

    def get_n_items(self):
        return self.n_items

    def get_timestamp(self):
        return self.timestamp


class MessageHarvester(Thread):
    """
    The thread to manage the consumption of the payload queue from the serial port reader
    This class takes the raw payload messages in dict form and enforces the SensorMessageItem contract
    and parses out special types into individual messages (for alerting, relay switching, etc.)
    """

    def __init__(self, payload_queue: Queue, sig_event: Event):
        super(MessageHarvester, self).__init__()

        # read in the global app config
        config = configparser.ConfigParser()
        config.read('config.cfg')

        self.logger = logging.getLogger(__name__)
        self.logger.info("Init MessageHarvester")
        self.sig_event = sig_event

        self.thread_sleep = config.getboolean('DEFAULT', 'thread_sleep')
        self.thread_sleep_time = config.getfloat('DEFAULT', 'thread_sleep_time')

        self.payload_queue = payload_queue

        self.api_sender = APIMessageWriter(sig_event)
        self.api_sender.start()

        self.enable_redis = config.getboolean('REDIS', 'redis_enable', fallback=False)

        self.redis_processor = None

        # keep track of total individual SensorMessageItem counts per mac
        self.count_stats_dict = dict()

        # keep track of timing stats per mac
        self.packet_timing_stats: dict[int, list] = dict()

        # the number of full payloads (lists of SensorMessageItems) we've received since epoch
        self.n_payloads_since_epoch: int = 0

        if self.enable_redis is True:
            self.redis_processor = RedisQueueReader(sig_event)
            self.redis_processor.start()

    def process_ev_cell_voltages(self, payload: dict) -> list[SensorMessageItem]:
        """
        Process the pipe delimited ext type for the 96 cell voltages
        :param payload: a payload dict where the data payload is pipe delimited floats
        :return: a list of SensorMessageItems
        """
        ret: list[SensorMessageItem] = list()

        try:
            voltages = [float(voltage) for voltage in payload['data'].split('|')]

            for i, voltage in enumerate(voltages):
                mac = int(payload['mac'])
                timestamp = int(payload['timestamp'])
                sensor_type = EVBatterySensorTypes.EV_BAT_CELL_VOLTAGES.value + i
                sensor_data = voltage
                ret.append(
                    SensorMessageItem(mac=mac,
                                      sensor_type=sensor_type,
                                      payload_data=sensor_data,
                                      timestamp=timestamp,
                                      sent=False))
        except Exception as e:
            self.logger.log("Error converting EV voltages into sensor messages:{}".format(e))

        return ret

    def process_sensor_messages(self, payload_items: list[dict]) -> list[SensorMessageItem]:
        """
        Process all the payload dicts into SensorMessageItem classes / contracts and handle special ext types
        :param payload_items:
        :return:
        """
        ret: list[SensorMessageItem] = list()

        for payload in payload_items:

            if int(payload['type']) == int(EVBatterySensorTypes.EV_BAT_CELL_VOLTAGES.value):
                [ret.append(item) for item in self.process_ev_cell_voltages(payload)]
            else:
                sensor_message = SensorMessageItem(mac=payload['mac'],
                                                   sensor_type=payload['type'],
                                                   timestamp=payload['timestamp'],
                                                   payload_data=payload['data'],
                                                   sent=False)
                ret.append(sensor_message)

        return ret

    def log_timing_stats(self, mac: int, timestamp: int):

        stats_dict_queue: list = self.packet_timing_stats.get(mac, None)

        if stats_dict_queue is None:
            stats_dict_queue = list()
            self.packet_timing_stats[mac] = stats_dict_queue

        if len(stats_dict_queue) > 200:
            stats_dict_queue.pop(0)

        stats_dict_queue.append(StatsQueueItem(timestamp, 0))

    def get_diffs(self, timestamps: list[int]):
        ret = list()
        for i, timestamp in enumerate(timestamps):
            if i < (len(timestamps) - 1):
                ret.append(timestamps[i + 1] - timestamps[i])
        return ret

    def output_timing_stats(self):

        for mac, stats_list in self.packet_timing_stats.items():
            if len(stats_list) >= 2:
                timestamps = [item.get_timestamp() for item in stats_list]
                diffs = self.get_diffs(timestamps)
                average = sum(diffs) / len(diffs)
                self.logger.info("Avg timing for {}: {}s".format(mac, str(round(average / 1000, 2))))
            else:
                self.logger.info("Not enough data to compute timing stats for:{}".format(mac))

    def log_count_stats(self, sensor_message_item: SensorMessageItem):

        mac_stats_dict = self.count_stats_dict.get(sensor_message_item.get_mac(), None)
        if mac_stats_dict is None:
            self.count_stats_dict[sensor_message_item.get_mac()] = {"total_count": 0}
            total_count = 0
        else:
            mac_stats_dict["total_count"] += 1
            total_count = mac_stats_dict["total_count"]

        if (total_count % 200) == 0:
            self.logger.info("Total messages processed for {}:{}".format(sensor_message_item.get_mac(), total_count))

    def run(self):
        self.logger.info("Enter MessageHarvester run()")
        while True:

            if self.sig_event.is_set():
                print("Exiting {}".format(self.__class__.__name__))
                self.api_sender.join(1000)
                break

            while not self.payload_queue.empty():

                payload_list = self.payload_queue.get()

                self.n_payloads_since_epoch += 1

                sensor_message_items = self.process_sensor_messages(payload_list)

                print("N sensor message items:{}".format(len(sensor_message_items)))
                print("N payloads received since epoch: {}".format(self.n_payloads_since_epoch))
                if len(sensor_message_items) < 1:
                    continue

                last_mac = -1

                for sensor_message_item in sensor_message_items:
                    last_mac = sensor_message_item.get_mac()
                    self.log_count_stats(sensor_message_item)

                self.log_timing_stats(last_mac, AretasUtils.now_ms())

                if (self.n_payloads_since_epoch % 10) == 0:
                    self.output_timing_stats()

                if self.enable_redis is True:
                    self.redis_processor.inject_messages(sensor_message_items)

                self.api_sender.enqueue_msgs(sensor_message_items)

            if self.thread_sleep is True:
                time.sleep(self.thread_sleep_time)
