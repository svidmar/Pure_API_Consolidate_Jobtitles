
# Job Title Consolidator Script for Elsevier's Pure

This script is designed to update person job title classifications in Pure based on a provided mapping table. This makes it possible to consolidate job titles, and delete reduntant classifications afterwards. It retrieves person records, modifies job title uri's according to a mapping table, and updates the person records via Pure's API.

## Features

- Fetches person records from Pure's API in batches.
- Maps current job classifications to new ones based on an Excel mapping table.
- Updates job titles via the Pure API with retry mechanisms for robust execution.
- Logs all actions for tracking and debugging.
- Includes a dry-run mode for testing without making actual updates.

## Requirements

- Python 3.x
- Libraries: `requests`, `pandas`, `tqdm`, `logging`, `openpyxl`

## Setup

1. Clone this repository and navigate to the directory.
2. Install the required libraries.
3. Replace instance-URL and API Key
4. Prepare an Excel file containing the mapping table with the following columns:
   - `current_classification`: The current classification URI.
   - `new_classification`: The new classification URI.

## Usage

### Running the Script

Run the script using:
```bash
python consolidate_jobtitles.py
```

### Parameters

The script accepts the following parameters:
- `mapping_table_path`: Path to the Excel mapping table (default: `mapping_final.xlsx`).
- `test_mode`: If `True`, limits the number of updates for testing purposes (default: `False`).
- `dry_run`: If `True`, performs a dry run without making updates to the Pure system (default: `True`).
- `test_limit`: Maximum number of updates in test mode (default: `100`).

### Logging

Logs are saved to `job_title_update.log` in the current directory.

### Processed UUIDs

Processed UUIDs are tracked in a `processed_uuids.txt` file to prevent duplicate processing.

## Notes

- Adjust the batch size (`size`) and API timeout settings (`REQUEST_TIMEOUT`) as needed based on your Pure's capacity
- Ensure the mapping table is accurate to prevent unintended updates!
- It only fetches/updates Person OrganizationAssociations, so visitingScholarOrganizationAssociations etc. are not included. 

## License

This script is provided as-is without any warranty. Use it responsibly and ensure proper testing before deployment in production.
