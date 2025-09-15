# initial_upload.py

import os
import firebase_admin
from firebase_admin import credentials, storage

# --- Configuration ---
# Your Firebase project's storage bucket URL
FIREBASE_STORAGE_BUCKET = 'data-driven-stock-analyzer' 
# The local directory containing your 'BSE' and 'NSE' folders
LOCAL_DATA_PATH = 'data/historical' 
# The top-level folder name to use in the cloud
CLOUD_STORAGE_FOLDER = 'raw_historical_data' 

def initial_upload():
    """
    Uploads raw historical data from local folders to Firebase Storage.
    """
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {'storageBucket': FIREBASE_STORAGE_BUCKET})
        print("Successfully initialized Firebase Admin SDK.")
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return

    bucket = storage.bucket()
    
    subfolders_to_upload = ['BSE', 'NSE']

    for folder in subfolders_to_upload:
        local_folder_path = os.path.join(LOCAL_DATA_PATH, folder)
        
        if not os.path.isdir(local_folder_path):
            print(f"Warning: Local directory not found, skipping: {local_folder_path}")
            continue

        files = os.listdir(local_folder_path)
        print(f"\nFound {len(files)} files in local folder '{local_folder_path}'. Starting upload...")

        for file_name in files:
            local_file_path = os.path.join(local_folder_path, file_name)
            cloud_file_path = f"{CLOUD_STORAGE_FOLDER}/{folder}/{file_name}"
            
            try:
                blob = bucket.blob(cloud_file_path)
                blob.upload_from_filename(local_file_path)
                print(f"  -> Uploaded {local_file_path} to {cloud_file_path}")
            except Exception as e:
                print(f"  -> FAILED to upload {local_file_path}. Error: {e}")

    print("\nInitial data upload process finished.")

if __name__ == "__main__":
    initial_upload()