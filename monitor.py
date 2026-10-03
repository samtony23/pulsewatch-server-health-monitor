import requests
import time
import subprocess
import socket
import mysql.connector
import os
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv


# -------------------------
# Load Environment Variables
# -------------------------

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


# -------------------------
# MySQL Connection
# -------------------------

def connect_database():

    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    return connection


# -------------------------
# Save Result to MySQL
# -------------------------

def save_result(service_name, check_type, status, response_time):

    connection = connect_database()
    cursor = connection.cursor()

    query = """
    INSERT INTO monitoring_results
    (service_name, check_type, status, response_time)
    VALUES (%s, %s, %s, %s)
    """

    values = (
        service_name,
        check_type,
        status,
        response_time
    )

    cursor.execute(query, values)
    connection.commit()

    cursor.close()
    connection.close()

    print("Result saved to MySQL")


# -------------------------
# Terminal Alert
# -------------------------

def send_alert(service_name, check_type):

    print()
    print("===================================")
    print("          ALERT")
    print("Service:", service_name)
    print("Check Type:", check_type)
    print("Status: DOWN")
    print("===================================")
    print()


# -------------------------
# Email Alert
# -------------------------

def send_email_alert(service_name, check_type):

    message = EmailMessage()

    message["Subject"] = (
        f"PulseWatch Alert: {service_name} is DOWN"
    )

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
            "smtp.gmail.com",
            465
        ) as server:

            server.login(
                EMAIL_ADDRESS,
                EMAIL_APP_PASSWORD
            )

            server.send_message(message)

        print("Email alert sent successfully.")

    except Exception as error:

        print("Email alert failed:", error)


# -------------------------
# Website HTTP Check
# -------------------------

def check_website(url):

    try:

        start_time = time.time()

        response = requests.get(
            url,
            timeout=5
        )

        end_time = time.time()

        response_time = end_time - start_time

        if response.status_code == 200:

            status = "UP"

        else:

            status = "DOWN"


        print("Website:", url)
        print("Status:", status)
        print("Status Code:", response.status_code)
        print(
            "Response Time:",
            round(response_time, 2),
            "seconds"
        )


        save_result(
            url,
            "HTTP",
            status,
            response_time
        )


        # Send alerts if website is DOWN

        if status == "DOWN":

            send_alert(
                url,
                "HTTP"
            )

            send_email_alert(
                url,
                "HTTP"
            )


        print("-------------------------")


    except requests.exceptions.RequestException:

        print("Website:", url)
        print("Status: DOWN")
        print("Reason: Website is not reachable")


        save_result(
            url,
            "HTTP",
            "DOWN",
            None
        )


        # Send alerts

        send_alert(
            url,
            "HTTP"
        )

        send_email_alert(
            url,
            "HTTP"
        )


        print("-------------------------")


# -------------------------
# Websites to Monitor
# -------------------------

websites = [

    "https://www.google.com",
    "https://www.github.com",
    "https://www.amazon.com"

]


for url in websites:

    check_website(url)


# -------------------------
# Ping Check
# -------------------------

def check_ping(host):

    result = subprocess.run(
        ["ping", "-n", "1", host],
        capture_output=True,
        text=True
    )


    if result.returncode == 0:

        status = "UP"

    else:

        status = "DOWN"


    print("Host:", host)
    print("Ping Status:", status)


    save_result(
        host,
        "PING",
        status,
        None
    )


    # Send alerts if ping is DOWN

    if status == "DOWN":

        send_alert(
            host,
            "PING"
        )

        send_email_alert(
            host,
            "PING"
        )


    print("-------------------------")


check_ping("google.com")


# -------------------------
# Port Check
# -------------------------

def check_port(host, port):

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        sock.settimeout(3)


        result = sock.connect_ex(
            (host, port)
        )


        if result == 0:

            status = "OPEN"

        else:

            status = "CLOSED"


        print("Host:", host)
        print("Port:", port)
        print("Port Status:", status)


        save_result(
            host,
            "PORT",
            status,
            None
        )


        # Send alerts if port is CLOSED

        if status == "CLOSED":

            send_alert(
                host,
                "PORT"
            )

            send_email_alert(
                host,
                "PORT"
            )


        sock.close()


    except socket.error:

        print("Unable to check the port.")


    print("-------------------------")


check_port(
    "google.com",
    443
)