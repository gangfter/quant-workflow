import time
import subprocess

def run():
    subprocess.run(["python", "engine/cross_signal_engine.py"])
    subprocess.run(["python", "-m", "engine.backtest_engine_v2"])
    subprocess.run(["python", "-m", "engine.performance_report_v2"])

if __name__ == "__main__":
    while True:
        print("\n=== CYCLE START ===")
        run()
        print("=== SLEEP 60s ===\n")
        time.sleep(60)