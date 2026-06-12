import time
import subprocess

def job():
    subprocess.run(["python", "engine/cross_signal_engine.py"])
    subprocess.run(["python", "-m", "engine.backtest_engine_v2"])

if __name__ == "__main__":
    while True:
        try:
            print("RUNNING CYCLE")
            job()
        except Exception as e:
            print("ERROR:", e)

        time.sleep(60)