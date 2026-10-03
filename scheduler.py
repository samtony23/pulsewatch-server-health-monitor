import subprocess
import sys
import time


print("Automatic monitoring started...")
print("Checks will run every 1 minute.")


while True:

    print("\nRunning monitoring checks...")

    try:

        subprocess.run(
            [sys.executable, "monitor.py"],
            check=True
        )

        print("Monitoring checks completed successfully.")

    except subprocess.CalledProcessError:

        print("Monitoring check failed.")


    print("Waiting 1 minute before the next check...")

    time.sleep(60)