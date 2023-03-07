import random
import math
import time
from matplotlib import pyplot as plt
from packet_mocker import TempMocker


def test_temp_mock_func():
    """

    """
    now = int(time.time() * 1000)

    one_hour_ms = 60 * 60 * 1000
    # the current ordinal hour value since epoch
    current_hour = now / one_hour_ms
    mocker = TempMocker()

    X = [x for x in range(0, 200)]
    y = [mocker.get_y(x) for x in X]

    plt.plot(X, y)
    plt.show()


if __name__ == "__main__":
    test_temp_mock_func()
