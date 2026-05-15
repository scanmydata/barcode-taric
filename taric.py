import os
import requests

def download_latest_circabc_taric():
    # Folder ID from user query
    folder_id = "2148dfe4-37c3-4a6b-9f63-3ebf06f279f8"
    api_url = f"https://europa.eu{folder_id}/children?p=1&n=20&sort=name_ASC"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code != 200:
            print("Error accessing API")
            return
            
        data = response.json()
        nodes = data.get("data", {}).get("nodes", [])
        
        # Identify the nomenclature file
        download_node = next((node for node in nodes if "nomenclature" in node.get("name", "").lower()), nodes[0])
            
        file_id = download_node.get("id")
        file_name = download_node.get("name")
        print(f"Downloading: {file_name}")
        
        # Direct download URL
        download_url = f"https://circabc.europa.eu/rest/download/{file_id}"
        file_response = requests.get(download_url, headers=headers, stream=True, timeout=60)
        
        if file_response.status_code == 200:
            with open(file_name, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"File saved: {file_name}")
        else:
            print("Download failed")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    download_latest_circabc_taric()
