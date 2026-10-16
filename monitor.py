import os
import time
import socket
import subprocess
import requests
import mysql.connector
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "health_monitor")

# Email configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")

# Monitoring targets
WEBSITES = [
    "https://www.google.com",
    "https://www.github.com",
    "https://www.amazon.com",
]

PING_HOSTS = ["google.com"]
PORT_CHECKS = [("google.com", 443)]


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        connection_timeout=10,
    )


def save_result(service_name, check_type, status, response_time=None):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO monitoring_results
                (service_name, check_type, status, response_time)
            VALUES (%s, %s, %s, %s)
            """,
            (service_name, check_type, status, response_time),
        )

        connection.commit()
        print("Result saved to MySQL")

    except mysql.connector.Error as error:
        print(f"MySQL error while saving result: {error}")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def update_incident(service_name, check_type, status):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if status == "DOWN":
            cursor.execute(
                """
                SELECT id FROM incidents
                WHERE service_name = %s
                  AND check_type = %s
                  AND status = 'OPEN'
                LIMIT 1
                """,
                (service_name, check_type),
            )

            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO incidents
                        (service_name, check_type, status)
                    VALUES (%s, %s, 'OPEN')
                    """,
                    (service_name, check_type),
                )
                connection.commit()
                send_email_alert(service_name, check_type)

        else:
            cursor.execute(
                """
                UPDATE incidents
                SET status = 'RESOLVED',
                    resolved_at = CURRENT_TIMESTAMP
                WHERE service_name = %s
                  AND check_type = %s
                  AND status = 'OPEN'
                """,
                (service_name, check_type),
            )
            connection.commit()

    except mysql.connector.Error as error:
        print(f"Incident tracking error: {error}")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def send_email_alert(service_name, check_type):
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD or not ALERT_EMAIL:
        print("Email alert skipped: email configuration is missing.")
        return False

    message = EmailMessage()
    message["Subject"] = f"PulseWatch Alert: {service_name} is DOWN"
    message["From"] = EMAIL_ADDRESS
    message["To"] = ALERT_EMAIL

    message.set_content(
        f"""PulseWatch Monitoring Alert

Service: {service_name}
Check Type: {check_type}
Status: DOWN

Please check the service immediately.
"""
    )

    try:
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, timeout=15
        ) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(message)

        print(f"Email alert sent for {service_name}.")
        return True

    except Exception as error:
        print(f"Email alert failed: {error}")
        return False


def check_website(url):
    start_time = time.perf_counter()
    status = "DOWN"
    response_time = None

    try:
        response = requests.get(url, timeout=10)
        response_time = time.perf_counter() - start_time
        status = "UP" if response.status_code < 400 else "DOWN"

        print(f"Website: {url}")
        print(f"Status: {status}")
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {response_time:.2f} seconds")

    except requests.RequestException as error:
        print(f"Website: {url}")
        print(f"Status: DOWN")
        print(f"Request error: {error}")

    save_result(url, "HTTP", status, response_time)
    update_incident(url, "HTTP", status)


def check_ping(host):
    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "3", host],
            capture_output=True,
            text=True,
            timeout=5,
        )
        status = "UP" if result.returncode == 0 else "DOWN"

    except (subprocess.SubprocessError, OSError):
        status = "DOWN"

    response_time = (
        time.perf_counter() - start_time if status == "UP" else None
    )

    print(f"Host: {host}")
    print(f"Ping Status: {status}")

    save_result(host, "PING", status, response_time)
    update_incident(host, "PING", status)


def check_port(host, port):
    start_time = time.perf_counter()

    try:
        with socket.create_connection((host, port), timeout=5):
            status = "UP"
            response_time = time.perf_counter() - start_time

    except (OSError, TimeoutError):
        status = "DOWN"
        response_time = None

    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Port Status: {'OPEN' if status == 'UP' else 'CLOSED'}")

    save_result(f"{host}:{port}", "PORT", status, response_time)
    update_incident(f"{host}:{port}", "PORT", status)


def run_checks():
    print("\n========== PulseWatch Monitoring ==========\n")

    for url in WEBSITES:
        check_website(url)
        print("-------------------------")

    for host in PING_HOSTS:
        check_ping(host)
        print("-------------------------")

    for host, port in PORT_CHECKS:
        check_port(host, port)
        print("-------------------------")

    print("\nMonitoring checks completed.")


if __name__ == "__main__":
    run_checks()
