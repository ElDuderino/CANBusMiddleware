import configparser
import logging
import time
from multiprocessing import Queue, Event
from threading import Thread

from api_message_writer import APIMessageWriter
from redis_message_processor import RedisQueueReader
from sensor_message_item import SensorMessageItem


class MessageHarvester(Thread):
    """
    The thread to manage the consumption of the payload queue from the serial port reader
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

        self.stats_dict = dict()

        self.redis_processor = None

        if self.enable_redis is True:
            self.redis_processor = RedisQueueReader(sig_event)
            self.redis_processor.start()

    def run(self):
        self.logger.info("Enter MessageHarvester run()")
        while True:

            if self.sig_event.is_set():
                print("Exiting {}".format(self.__class__.__name__))
                self.api_sender.join(1000)
                break

            while not self.payload_queue.empty():

                payload_list = self.payload_queue.get()

                sensor_message_items = [SensorMessageItem(mac=payload['mac'],
                                                          sensor_type=payload['type'],
                                                          timestamp=payload['timestamp'],
                                                          payload_data=payload['data'],
                                                          sent=False)
                                        for payload in payload_list]

                for sensor_message_item in sensor_message_items:

                    mac_stats_dict = self.stats_dict.get(sensor_message_item.get_mac(), None)
                    if mac_stats_dict is None:
                        self.stats_dict[sensor_message_item.get_mac()] = {"total_count": 0}
                        total_count = 0
                    else:
                        mac_stats_dict["total_count"] += 1
                        total_count = mac_stats_dict["total_count"]

                    if (total_count % 200) == 0:
                        self.logger.info("Total messages processed:{}".format(total_count))

                if self.enable_redis is True:
                    self.redis_processor.inject_messages(sensor_message_items)

                self.api_sender.enqueue_msgs(sensor_message_items)

            if self.thread_sleep is True:
                time.sleep(self.thread_sleep_time)
