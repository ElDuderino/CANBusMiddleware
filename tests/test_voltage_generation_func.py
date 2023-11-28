import numpy as np
import datetime
import time
import scipy.signal as sg
from matplotlib import pyplot as plt

"""
Test out some data mocking functions and plot the output
"""


def sine_wave(x, min_max_range, frequency):
    min_val, max_val = min_max_range
    amplitude = (max_val - min_val) / 2

    # Convert frequency from milliseconds to seconds
    frequency_sec = frequency / 1000.0

    # Generate the sine wave
    y = amplitude * np.sin(2 * np.pi * (x / frequency_sec)) + amplitude + min_val

    return y


def triangle_wave_sg(x, min_max_range, frequency):
    min_val, max_val = min_max_range
    amplitude = (max_val - min_val)
    y = amplitude * sg.sawtooth(frequency * 2 * np.pi * x, width=0.5)
    return y


def triangle_wave(x, min_max_range, frequency):
    min_val, max_val = min_max_range
    amplitude = (max_val - min_val)
    min_val = min_val - amplitude

    # Convert frequency from milliseconds to seconds for compatibility with numpy
    frequency_sec = frequency / 1000.0

    # Generate the triangle wave
    y = amplitude * np.abs(2 * (x / frequency_sec - np.floor(0.5 + x / frequency_sec))) + amplitude + min_val

    return y


def triangle_wave_n(x, min_max_range, frequency):
    """
    This is the best candidate for triangle "wave" output
    :param x:
    :param min_max_range:
    :param frequency:
    :return:
    """
    min_val, max_val = min_max_range
    A = max_val - min_val
    P = frequency

    y = (A / P) * (P - np.abs(x % (2 * P) - P)) + min_val

    return y


def plot_values(x_values, y_values, title):
    # Convert current time in milliseconds to a datetime object
    current_time = int(time.time() * 1000)
    current_datetime = datetime.datetime.fromtimestamp(current_time / 1000)

    # Create future datetime objects by adding x values (milliseconds) to current time
    x_datetimes = [current_datetime + datetime.timedelta(milliseconds=int(x)) for x in x_values]

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(x_datetimes, y_values, label='Values')
    plt.xlabel('Time')
    plt.ylabel('Values')
    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend()
    plt.show()


if __name__ == "__main__":
    time_range = 4 * 60 * 60 * 1000  # 4 hour
    interval = 10000  # every 10 seconds
    n_values = int(time_range / interval)

    x_values = np.linspace(0, time_range, n_values)  # x values in milliseconds
    min_max_range = (3.0, 4.3)  # Simulated temperature range

    # how often does the value go through a half cycle
    frequency = 1 * 60 * 60 * 1000 / 2  # Frequency in milliseconds (1 hours)

    voltage_values = triangle_wave_n(x_values, min_max_range, frequency)

    plot_values(x_values, voltage_values, 'Simulated Values Over Time')
