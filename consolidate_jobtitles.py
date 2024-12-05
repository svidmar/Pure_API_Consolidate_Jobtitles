import requests
import pandas as pd
import logging
import time
from tqdm import tqdm
import os

# Configure logging
logging.basicConfig(
    filename='job_title_update.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants for processed UUIDs file
PROCESSED_UUIDS_FILE = "processed_uuids.txt"

# API configuration
BASE_URL = "https://xyz.elsevierpure.com/ws/api/persons" #Replace instance-URL
API_KEY = "PURE_API_KEY"  # Replace with API key
HEADERS = {"accept": "application/json", "api-key": API_KEY}
PUT_HEADERS = {
    "Content-Type": "application/json",
    "accept": "application/json",
    "api-key": API_KEY
}

# Timeout and retry configuration
REQUEST_TIMEOUT = (5, 15)  # (connect timeout, read timeout)
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Load processed UUIDs
def load_processed_uuids():
    if os.path.exists(PROCESSED_UUIDS_FILE):
        with open(PROCESSED_UUIDS_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()

# Save a processed UUID
def save_processed_uuid(uuid):
    with open(PROCESSED_UUIDS_FILE, "a") as f:
        f.write(f"{uuid}\n")

# Read mapping table
def load_mapping_table(filepath):
    try:
        df = pd.read_excel(filepath)
        return dict(zip(df['current_classification'], df['new_classification']))
    except Exception as e:
        logging.error(f"Failed to load mapping table: {e}")
        raise

# Fetch persons from Pure's API with retry mechanism
def fetch_persons(offset, size):
    url = f"{BASE_URL}?offset={offset}&size={size}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout occurred when fetching persons (attempt {attempt}/{MAX_RETRIES}). Retrying...")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error during fetch_persons: {e} (attempt {attempt}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY)
    logging.error(f"Failed to fetch persons after {MAX_RETRIES} attempts.")
    return None

# Update job title via PUT request with retry mechanism
def update_person(uuid, staff_organization_associations, dry_run):
    url = f"{BASE_URL}/{uuid}"
    data = {"staffOrganizationAssociations": staff_organization_associations}
    if dry_run:
        logging.info(f"DRY RUN: Would update person {uuid} with updated job titles.")
        return
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.put(url, headers=PUT_HEADERS, json=data, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                logging.info(f"Successfully updated person {uuid}")
                return
            else:
                logging.error(f"Failed to update person {uuid}: {response.status_code} - {response.text}")
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout occurred when updating person {uuid} (attempt {attempt}/{MAX_RETRIES}). Retrying...")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error during update_person for UUID {uuid}: {e} (attempt {attempt}/{MAX_RETRIES})")
        time.sleep(RETRY_DELAY)
    logging.error(f"Failed to update person {uuid} after {MAX_RETRIES} attempts.")

# Main function
def main(mapping_table_path, test_mode=False, dry_run=True, test_limit=100):
    mapping = load_mapping_table(mapping_table_path)
    logging.info("Loaded mapping table.")

    size = 100  # Batch size for API calls
    offset = 0
    total_processed = 0

    # Load processed UUIDs
    processed_uuids = load_processed_uuids()

    # Fetch the total count for progress tracking
    initial_response = fetch_persons(0, 1)
    if not initial_response:
        logging.error("Failed to fetch initial count. Exiting.")
        return
    total_count = initial_response.get("count", 0)
    logging.info(f"Total persons to process: {total_count}")

    # Progress bar
    with tqdm(total=total_count, desc="Processing Persons", unit="person") as pbar:
        while True:
            response = fetch_persons(offset, size)
            if not response:
                break

            items = response.get("items", [])
            count = response.get("count", 0)

            for person in items:
                uuid = person["uuid"]
                if uuid in processed_uuids:
                    logging.info(f"Skipping already processed UUID: {uuid}")
                    pbar.update(1)
                    continue

                staff_organization_associations = person.get("staffOrganizationAssociations", [])

                # Check and modify job titles
                updated = False
                all_match = True
                for association in staff_organization_associations:
                    job_title = association.get("jobTitle", {})
                    current_uri = job_title.get("uri")
                    if current_uri in mapping:
                        new_uri = mapping[current_uri]
                        if current_uri != new_uri:
                            job_title["uri"] = new_uri
                            updated = True
                            logging.info(f"Modified job title for person {uuid}: {current_uri} -> {new_uri}")
                        else:
                            all_match = all_match and True
                    else:
                        all_match = all_match and True

                # Skip update if all classifications match
                if all_match and not updated:
                    logging.info(f"No changes required for person {uuid}. Skipping PUT request.")
                    save_processed_uuid(uuid)
                    pbar.update(1)
                    continue

                if updated:
                    # Update the entire staffOrganizationAssociations object
                    update_person(uuid, staff_organization_associations, dry_run)
                    total_processed += 1
                    save_processed_uuid(uuid)

                    if test_mode and total_processed >= test_limit:
                        logging.info("Test mode limit reached. Exiting.")
                        return

                pbar.update(1)

            offset += size
            if offset >= count:
                break

            # Sleep periodically to avoid hitting Pure's API too hard
            time.sleep(1)

    logging.info(f"Completed processing. Total persons processed: {total_processed}")

if __name__ == "__main__":
    # Path to the Excel mapping table and file
    mapping_table_path = "mapping_final.xlsx"

    # Run the script with dry run enabled to test changes without making updates
    main(mapping_table_path, test_mode=False, dry_run=True, test_limit=100)
