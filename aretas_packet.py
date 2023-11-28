from AretasPythonAPI.utils import Utils as AretasUtils
import logging


class AretasPacket:

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_packet(self, buffer: bytes, default_mac: int = None) -> dict or None:
        """
        Parse a bytestring we read in off the UART and
        turn it into a standard packet like Aretas uses for everything
        """

        str_packet = buffer.decode('utf-8')
        str_tok = str_packet.split(',')

        if len(str_tok) != 3:
            self.logger.error("Incorrect packet length {0} for string:{1}".format(len(str_tok), str_packet))
            return None

        try:

            mac_ = int(str_tok[0])
            type_ = int(str_tok[1])
            # don't coerce the data to float, since we need to support ext types
            data_ = str_tok[2]

            if default_mac is not None:
                mac_ = default_mac

            return {
                'mac': mac_,
                'timestamp': AretasUtils.now_ms(),
                'type': type_,
                'data': data_
            }

        except Exception as e:
            self.logger.error("Couldn't parse bytestring {}".format(e))
            return None
