from flask import Flask, render_template
import mysql.connector
import subprocess
import sys
import os

from dotenv import load_dotenv


# -------------------------
# Load Environment Variables
# -------------------------

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


# -------------------------
# Flask Application
# -------------------------

app = Flask(__name__)


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
# Run Monitoring Checks
# -------------------------

@app.route("/run-checks")
def run_checks():

    subprocess.run(
        [sys.executable, "monitor.py"],
        check=True
    )

    return """
    <h2>Monitoring checks completed successfully!</h2>

    <br>

    <a href="/">Go back to Dashboard</a>
    """


# -------------------------
# Dashboard
# -------------------------

@app.route("/")
def home():

    connection = connect_database()
    cursor = connection.cursor(dictionary=True)


    # -------------------------
    # Get all monitoring results
    # -------------------------

    cursor.execute("""
        SELECT *
        FROM monitoring_results
        ORDER BY checked_at DESC
    """)

    results = cursor.fetchall()


    # -------------------------
    # Total checks
    # -------------------------

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM monitoring_results
    """)

    total = cursor.fetchone()["total"]


    # -------------------------
    # Healthy checks
    # -------------------------

    cursor.execute("""
        SELECT COUNT(*) AS healthy
        FROM monitoring_results
        WHERE status IN ('UP', 'OPEN')
    """)

    healthy = cursor.fetchone()["healthy"]


    # -------------------------
    # Unhealthy checks
    # -------------------------

    cursor.execute("""
        SELECT COUNT(*) AS unhealthy
        FROM monitoring_results
        WHERE status IN ('DOWN', 'CLOSED')
    """)

    unhealthy = cursor.fetchone()["unhealthy"]


    # -------------------------
    # Overall uptime
    # -------------------------

    if total > 0:

        uptime = (healthy / total) * 100

    else:

        uptime = 0


    # -------------------------
    # Service-wise uptime
    # -------------------------

    cursor.execute("""
        SELECT
            service_name,
            COUNT(*) AS total_checks,
            SUM(
                CASE
                    WHEN status IN ('UP', 'OPEN')
                    THEN 1
                    ELSE 0
                END
            ) AS healthy_checks
        FROM monitoring_results
        GROUP BY service_name
        ORDER BY service_name
    """)

    service_uptime = cursor.fetchall()


    # Calculate uptime percentage

    for service in service_uptime:

        if service["total_checks"] > 0:

            service["uptime"] = (
                service["healthy_checks"]
                / service["total_checks"]
            ) * 100

        else:

            service["uptime"] = 0


    # -------------------------
    # Close database
    # -------------------------

    cursor.close()
    connection.close()


    # -------------------------
    # Send data to dashboard
    # -------------------------

    return render_template(
        "index.html",
        results=results,
        total=total,
        healthy=healthy,
        unhealthy=unhealthy,
        uptime=uptime,
        service_uptime=service_uptime
    )


# -------------------------
# Run Flask
# -------------------------

if __name__ == "__main__":

    app.run(debug=True)