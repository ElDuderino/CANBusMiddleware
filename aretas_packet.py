from AretasPythonAPI.utils import Utils as AretasUtils
import logging


class AretasPacket:

    @staticmethod
    def parse_packet(buffer: bytes) -> dict or None:
        """
        Parse a bytestring we read in off the UART and
        turn it into a standard packet like Aretas uses for everything
        """

        logger = logging.getLogger(__name__)

        str_packet = buffer.decode('utf-8')
        str_tok = str_packet.split(',')

        if len(str_tok) != 3:
            logger.error("Incorrect packet length {0} for string:{1}".format(len(str_tok), str_packet))
            return None

        try:

            mac_ = int(str_tok[0])
            type_ = int(str_tok[1])
            data_ = float(str_tok[2])

            return {
                'mac': mac_,
                'timestamp': AretasUtils.now_ms(),
                'type': type_,
                'data': data_
            }

        except Exception as e:
            logger.error("Couldn't parse bytestring {}".format(e))
            return None


