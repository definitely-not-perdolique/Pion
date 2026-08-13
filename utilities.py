import time

def active_sleep(seconds):
    starttime = time.time()

    while time.time() - starttime < seconds:
        time.sleep(1)