import configparser
from queue import Queue
from threading import Thread, Event
from AretasPythonAPI.utils import Utils as AretasUtils
from AretasPythonAPI.api_config import *
from AretasPythonAPI.auth import *
from AretasPythonAPI.sensor_data_ingest import *
from sensor_message_item import SensorMessageItem


class APIMessageWriter(Thread):
    """
    This class writes the data to API
    inject data into this class by enqueue_msg
    Create an instance of this Thread and run it
    The data will be sent every report_interval milliseconds as specified in the config
    """
    def __init__(self, sig_event: Event):

        super(APIMessageWriter, self).__init__()

        self.logger = logging.getLogger(__name__)
        self.sig_event = sig_event

        # read in the global app config
        config = configparser.ConfigParser()
        config.read('config.cfg')

        self.last_message_time = 0
        self.polling_interval = config.getint('API', 'report_interval')

        self.api_config = APIConfig()
        self.api_auth = APIAuth(config)
        self.api_writer = SensorDataIngest(self.api_auth)

        # a hashmap of sensor messages we want to send to the API
        self.to_send = dict([int, SensorMessageItem])

        self.is_sending = False

    def enqueue_msg(self, message: SensorMessageItem):
        """
        Enqueue a message to be sent, the message may or may not be sent as it may be overwritten
        by a new value before being sent
        This thread manages its own send intervals and this function just
        adds the datum to a key/value store (indexed by sensor type)
        As such the key/value store index for a particular sensor type just gets overwritten by new data
        A flag is set in the dict entry to indicate if it has been sent or not
        New messages added to the dict always have the is_sent flag set to False
        """
        # don't accept new messages if we're in the process of sending
        # it's unlikely this will ever happen but...
        if self.is_sending is False:
            dict_key = message.get_type()
            # we're going to assert that it has not been sent
            message.set_is_sent(False)
            self.to_send[dict_key] = message
        return

    def run(self):
        """
        We send any of the messages in the self.to_send hashmap only if they have not
        been flagged as sent
        """
        while True:
            if self.sig_event.is_set():
                self.logger.info("Exiting {}".format(self.__class__.__name__))
                break

            now_ = AretasUtils.now_ms()
            if (now_ - self.last_message_time) >= self.polling_interval:
                self.logger.info("Sending messages to API")
                self.last_message_time = now_
                # use the apiwriter
                self.is_sending = True

                for message in self.to_send:
                    # if it hasn't been previously sent, then send it
                    if not message.get_is_sent():
                        datum: dict = {
                            'mac': message.get_mac(),
                            'type': message.get_type(),
                            'timestamp': message.get_timestamp(),
                            'data': message.get_data()
                        }
                        # we're using the token self-management function
                        err = self.api_writer.send_datum_auth_check(datum)
                        if err is False:
                            self.logger.error("Error sending messages, aborting rest")
                            break
                        else:
                            message.set_is_sent(True)

                self.is_sending = False
                pass
