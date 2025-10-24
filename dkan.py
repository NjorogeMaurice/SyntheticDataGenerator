import re
from pathlib import Path

import requests


class DataCatalogFetchAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.save_path = "save_path"
        self.saved_urls = []

    # Function to download data and save it to a file
    def download_data(self, url, save_path):
        try:
            response = requests.get(url, timeout=10)  # Set a timeout for requests
            response.raise_for_status()  # Raise an error for unsuccessful status codes
            self.saved_urls.append(url)
            return True
        except requests.RequestException as e:
            print(f"Failed to fetch data from: {url} | Error: {e}")
            return False

    # Function to fetch the list of datasets
    def get_dataset_list(self):
        response = requests.get(self.base_url+"/api/3/action/package_list")
        return response.json().get("result") if response.status_code == 200 else None

    def get_dataset_resources(self):
        dataset_list=self.get_dataset_list()
        if dataset_list is None:
            raise ValueError("Dataset list is empty or could not be retrieved.")

        for dataset_id in dataset_list:
            self.get_individual_dataset(dataset_id)

        return self.saved_urls


    def get_individual_dataset(self,dataset_id):
        # Fetch the dataset metadata
        response = requests.get(self.base_url+"/api/3/action/package_show", params={"id": dataset_id})
        if response.status_code == 200:
            data = response.json()


            # Check if the response contains 'result' and then 'resources'
            if data.get("result") and any(result.get("resources") for result in data["result"]):
                resources = data["result"][0]['resources']
                extracted_urls=[]
                index=0

                # Display the resources JSON array
                for resource in resources:
                    # Regex to extract the URL inside the HTML
                    match = re.search(r'>(https?://[^\s<>]+)<', resource["url"])

                    if match:
                        url = match.group(1)
                        if url.lower().endswith(".csv"):  # Check if URL ends with .csv (case insensitive)
                            extracted_urls.append(url)
                    else:
                        try:
                            resource_file_name=resource["name"]+"."+resource["format"]
                            if resource["url"].lower().endswith(".csv"):
                                self.download_data(resource["url"], Path(f"{self.save_path}/{resource_file_name}"))
                        except Exception as e:
                            print(f"Failed to download data from {resource['url']}: {e}")

                if len(extracted_urls)>0:
                    for url in extracted_urls:
                        file_name=resources[index]["name"]
                        if self.download_data(url,Path(f"{self.save_path}/{file_name}")):
                            break
                        index=+1
            else:
                print("Resources not found in the response.")
        else:
            print(f"Error fetching dataset: {response.status_code}")
