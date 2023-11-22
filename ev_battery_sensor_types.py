from enum import Enum


class EVBatterySensorTypes(Enum):
    """
    An enum class mapping types to integers compatible with the Aretas sensor metadata canon
    Note that we'll write these first then add to the Aretas API
    """
    # high voltage battery's health
    EV_BAT_HX = 0x201

    # state of charge of the HV battery
    EV_BAT_SOC = 0x202

    # Capacity of HV battery (how much energy the battery [sic] could hold when fully charged
    EV_BAT_AHR = 0x203

    # High voltage battery current. Positive when driving, negative when regen braking or charging
    EV_BAT_HV_BAT_CURRENT_1 = 0x204

    # Unclear why there are two.. but there are!
    EV_BAT_HV_BAT_CURRENT_2 = 0x205

    # High voltage battery voltage
    EV_BAT_HV_BAT_VOLTAGE = 0x206

    # cells voltage - this is the voltages (in mV) from the N cell pairs (96 in the leaf for example)
    # we will not support this directly right now, but will, in the future, as an extended type
    EV_BAT_CELL_VOLTAGES = 0x258

    # packs temperatures (degrees C)
    EV_BAT_TEMP_1 = 0x208
    EV_BAT_TEMP_2 = 0x209
    EV_BAT_TEMP_3 = 0x20A
    EV_BAT_TEMP_4 = 0x20B

    EV_BAT_SHUNTS = 0x20C

    # State of Health is another indication of the battery’s ability to hold and release energy and is
    # reported as a percentage. When the battery is new SOH=100%
    EV_BAT_SOH = 0x20D

    # consider overriding str to send back proper descriptions
    # __str__(self):
