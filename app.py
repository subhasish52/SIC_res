from flask import Flask, request, jsonify, send_from_directory, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import shutil
import traceback

app = Flask(__name__)

# Credentials for ERP login
USERNAME = "23bcsb02"
PASSWORD = "Subhasish@6901"

# Path to ChromeDriver
chromedriver_path = "C:\\Users\\subha\\Downloads\\chromedriver-win64\\chromedriver.exe"

# Verify ChromeDriver exists
if not os.path.isfile(chromedriver_path):
    raise FileNotFoundError(f"ChromeDriver not found at: {chromedriver_path}")

# Define download directory
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def download_pdf_for_sic(sic_number):
    print(f"[INFO] Processing SIC: {sic_number}...")

    # Clear the downloads directory before starting
    print("[INFO] Clearing downloads directory...")
    shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
    os.makedirs(DOWNLOAD_DIR)

    # Set up Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    })

    # Initialize ChromeDriver
    try:
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        print("[INFO] ChromeDriver initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize ChromeDriver: {str(e)}")
        print(traceback.format_exc())
        return None

    try:
        print("[INFO] Navigating to login page...")
        driver.get("https://erp.silicon.ac.in/estcampus/index.php")

        print("[INFO] Logging in...")
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.send_keys(USERNAME)
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(PASSWORD)
        signin_button = driver.find_element(By.XPATH, "//button[text()='Sign in']")
        signin_button.click()

        print("[INFO] Waiting for login to complete...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("[INFO] Logged in successfully!")

        print("[INFO] Navigating to result page...")
        result_url = "https://erp.silicon.ac.in/estcampus/autonomous_exam/exam_result.php?role_code=M1Z5SEVJM2dub0NWWE5GZy82dHh2QT09"
        driver.get(result_url)

        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        print(f"[INFO] Triggering PDF download for SIC: {sic_number}...")
        driver.execute_script(f"Final_Semester_Result_pdf_Download('{sic_number}')")

        # Wait for the PDF to download
        print("[INFO] Waiting for PDF download to complete...")
        timeout = 30  # Wait up to 30 seconds
        start_time = time.time()
        downloaded_file = None
        while time.time() - start_time < timeout:
            for filename in os.listdir(DOWNLOAD_DIR):
                if filename.endswith(".pdf"):
                    downloaded_file = os.path.join(DOWNLOAD_DIR, filename)
                    print(f"[INFO] Found PDF: {filename}")
                    break
            if downloaded_file:
                break
            time.sleep(1)  # Check every second

        if downloaded_file:
            # Rename the file to match the SIC number
            new_filename = f"{sic_number}.pdf"
            new_file_path = os.path.join(DOWNLOAD_DIR, new_filename)
            os.rename(downloaded_file, new_file_path)
            print(f"[INFO] Renamed PDF to: {new_filename}")
            return new_file_path
        else:
            print("[WARNING] No PDF found in downloads directory after waiting.")
            return None

    except Exception as e:
        print(f"[ERROR] An error occurred: {str(e)}")
        print(traceback.format_exc())
        return None
    finally:
        driver.quit()
        print("[INFO] Browser closed. Process complete!")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_pdf():
    try:
        data = request.json
        if not data or 'sic' not in data:
            return jsonify({"error": "No SIC number provided"}), 400
        
        new_sic = data['sic'].strip().upper()
        if len(new_sic) != 8:
            return jsonify({"error": "SIC must be exactly 8 characters"}), 400
        
        full_sic = f"SITBBS{new_sic}"
        pdf_path = download_pdf_for_sic(full_sic)
        
        if pdf_path and os.path.exists(pdf_path):
            pdf_filename = os.path.basename(pdf_path)
            return jsonify({"message": "PDF downloaded successfully", "pdf": pdf_filename}), 200
        else:
            return jsonify({"error": "Failed to download PDF"}), 500
    except Exception as e:
        print(f"[ERROR] Exception in /download: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

@app.route('/downloads/<filename>')
def serve_pdf(filename):
    try:
        return send_from_directory(DOWNLOAD_DIR, filename)
    except Exception as e:
        print(f"[ERROR] Exception in /downloads: {str(e)}")
        return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)