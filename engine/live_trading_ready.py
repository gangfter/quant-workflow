import subprocess
import time

def cycle():
    subprocess.run(["python", "engine/cross_signal_engine.py"])
    subprocess.run(["python", "-m", "engine.backtest_engine_v2"])
    subprocess.run(["python", "-m", "engine.performance_report_v2"])

if __name__ == "__main__":
    print("LIVE TRADING LOOP STARTED")

    while True:
        try:
            cycle()
        except Exception as e:
            print("ERROR:", e)

        time.sleep(60)
        