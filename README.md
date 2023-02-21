# CAN Bus Middleware #

Currently, this middleware connects an EV battery CAN Bus decoder to the Aretas cloud platform

However, we intend to support other CAN bus sensor data to enable extensive EV, HEV and ICE telematics. 

The connections:

EV Battery<--(can bus)-->RP2040 board<--(USB)-->Raspberry Pi<--(Ethernet/WiFI)-->Aretas Cloud

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

## Running ##
Will include more info here eventually, but to run it now, just run ``python3 backend_daemon.py``

## Notes ##

### Sensortype Metadata ###
I need to decide on the actual integer (uint_16) types for the new sensor types to avoid collisions with existing types in the Aretas API.
Please have a look at ``new_sensor_types.json`` for an example of how these come out of the public endpoint. 

I'll  create a reserved block for telematics types and start sketching them out in the API

### K.I.S.S. Data Format ##
The Aretas payload format over UART is:
- mac - 32-bit integer (unique device identifier)
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

Also, be aware, all the types are being sent to the API serially and synchronously right now. 
As such, if the API send takes 10ms, sending 10 sensor types takes 10*10ms = 100ms

Batch mode is supported in the API but not in the SDK yet, so that is coming soon.


## Packet Mocker ##
Description coming soon