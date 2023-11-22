from api_message_writer import APIMessageWriter
import configparser
import sys
import os

# read in the global app config
config = configparser.ConfigParser()
config.read('config.cfg')

ignore_types = APIMessageWriter.parse_ignore_types(config.get('API', 'ignore_types', fallback=""))

print(ignore_types)

print((650 in ignore_types))
