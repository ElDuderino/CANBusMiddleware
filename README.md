# CAN Bus Middleware #

Currently, this middleware connects multiple EV battery CAN Bus decoders to the Aretas cloud platform

The current LEAF Decoder firmware can be found here. It's targeted to the Longan RP2040 board but should work with minor 
modifications on any Arduino CANBUS board:
https://github.com/ElDuderino/CANBedFirmware 
If you want to use an Aretas or other CANBUS board other than Longan RP2040 based board, you will likely need 
to change libraries and adjust the firmware slightly.

We intend to support other CAN bus sensor data to enable extensive EV, HEV and ICE telematics. 

The connections:

EV Battery(ies)<--(can bus)-->RP2040 board<--(USB)-->Raspberry Pi<--(Ethernet/WiFI)-->Aretas Cloud

We intend to support the following sensor data:
1. Hx % - High voltage battery's health
2. SOC % - State of charge of the HV Battery
3. Ahr - Capacity of EV Battery e.g. how much energy the battery [sic] *could hold when charged.
4. HV_Bat_Current_1 - The high voltage battery current (positive when driving / running and negative when regenerative braking or charging)
5. HV_Bat_Current_2 - A second current indicator, not clear why
6. HV_Bat_Voltage - The High Voltage battery voltage
7. Cells Voltage mV - The 96 cell pair voltages in millivolts. We will support this as an extension to the ext sensor types in the platform.
8. Packs temperature - the 4 temperature sensor readings in degrees C
9. SOH % - State of health indicator (0 - 100%). An indicator of the battery's ability to hold and release energy

## Cloud Features ##

The middleware will get the data in to the cloud and give us access to all the current dashboards in the Aretas platform and:
- Support as many batteries / locations as we want
- Support all sensors out of the box
- Support Alerting on any sensor data (Current usage, Battery Condition, etc.)
- Historical Analytics
- AI data labeling and AI microservice support
- Live data charts / streams
- Condition reports 

## Running ##
Edit config.cfg to make sure you:
- disable packet mocking
- have valid credentials for the Aretas API
- enter the correct COM port(s) for the serial connection
- Ensure you have entered at least one valid port,mac combo
- PLEASE leave the ignore_types intact for now and DO NOT send cell voltages to the cloud. We plan to support this
as an ext type in the future, but for now it will seriously break your user experience in the analytics platform if you send them.
- The 96 cell voltages ARE sent to REDIS for use with the BanBangController or other things. 

Will include more info here eventually, but to run it now, just run ``python3 backend_daemon.py``

## Notes ##

### Redis ###
You can support an optional REDIS connection. The current functionality is very, very basic. We call HSET with the MAC,TYPE
and insert one SensorDatum. New SensorDatums overwrite the old ones. Extend it if you want. 
For BESS systems, the REDIS message format works with: 
https://github.com/ElDuderino/BangBangController
This enables threshold control for the various parameters that come out of the battery. 

To enable Relay control, you need a Waveshare Pico Relay B
You must load this firmware on to the Pico: https://github.com/ElDuderino/RP2040SerialGPIOControl

### Sensortype Metadata ###
I need to decide on the actual integer (uint_16) types for the new sensor types to avoid collisions with existing types in the Aretas API.
Please have a look at ``new_sensor_types.json`` for an example of how these come out of the public endpoint. 

I'll  create a reserved block for telematics types and start sketching them out in the API

### K.I.S.S. Data Format ##
The Aretas payload format over UART is:
- mac - 48-bit integer (unique device identifier)
- type - 16-bit integer (sensor type)
- data - float (the payload data)

You write a **String** representation comma separated, over the UART
E.g. 
``mac,type,data\n``

The serial reader then reads until \n and parses the buffer. Invalid packets are discarded. 
We don't need anything else. Despite not being efficient, this method is easy to debug, easy to code for and just works.

If we find a need to migrate to a more complex / efficient packet format down the road, it's an easy port.

### Timestamps ###
All timestamps in the Aretas platform are UNIX Epoch millisecond precision
To keep everything standardized please use the Utils.now_ms() function in utils.py in the AretasPythonAPI
Timestamps are added to each packet by the middleware.

### Cloud API Datarate ###

In the config file, there is an item called ``report_interval = 10000`` This value sets the rate at which we send data to the API.
The UART may be streaming data faster than this and that's ok. 
However, we only send the *latest* data packets **for every type** every ``report_interval`` milliseconds
I.e. if we have 10 different sensor types all 10 are sent at once.
Any new packets arriving between the last time data was sent and just before the next send data interval are overwritten
This is to prevent spamming the API excessively with too much data

Eventually we can submit cache only data which will persist in the cache, but not require a database write for every packet.

~~Also, be aware, all the types are being sent to the API serially and synchronously right now. 
As such, if the API send takes 10ms, sending 10 sensor types takes 10*10ms = 100ms~~ Messages are sent in batch mode now.

Batch mode is supported in the API but not in the SDK yet, so that is coming soon.


## Packet Mocker ##
Description coming soon
