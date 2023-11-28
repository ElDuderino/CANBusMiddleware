from packet_mocker import CellMocker
from AretasPythonAPI.utils import Utils as AretasUtils
from matplotlib import pyplot as plt
import time
import datetime


def plot_mocker(x_values, y_values, title):
    # Convert current time in milliseconds to a datetime object
    current_time = int(time.time() * 1000)
    current_datetime = datetime.datetime.fromtimestamp(current_time / 1000)

    # Create future datetime objects by adding x values (milliseconds) to current time
    x_datetimes = [current_datetime + datetime.timedelta(milliseconds=int(x)) for x in x_values]

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(x_datetimes, y_values, label='Voltage')
    plt.xlabel('Time')
    plt.ylabel('Voltage')
    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend()
    plt.show()


if __name__ == "__main__":

    cell_mocker = CellMocker()

    now = AretasUtils.now_ms()

    ys = list()
    xs = list()

    interval = 10000
    time_range = 4 * 60 * 60 * 1000

    for i in range(int(time_range / interval)):
        t_diff = i * interval
        xs.append(t_diff + now)
        ys.append(cell_mocker.get_next_value(now=t_diff + now))

    print(len(ys))
    plot_mocker(xs, ys, "mocked values")
