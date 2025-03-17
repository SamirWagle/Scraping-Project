import os
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

BASE_URL = "https://www.thecountyrecorder.com"

def get_initial_hidden_fields(session):
    """Fetch initial VIEWSTATE and EVENTVALIDATION values"""
    response = session.get(BASE_URL)
    soup = BeautifulSoup(response.text, 'html.parser')

    viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
    eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]
    
    return viewstate, eventvalidation

# Function to select state

def select_state(session, state, viewstate, eventvalidation):
    """Select a state and fetch updated hidden fields"""
    response = session.get(BASE_URL)
    
    if response.status_code != 200:
        print("Failed to load the state selection page.")
        return None, None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract updated hidden fields for form submission
    viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
    eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]

    # Find the correct state value from dropdown
    state_dropdown = soup.find("select", {"id": "MainContent_searchMainContent_ctl01_ctl00_cboStates"})
    state_value = None
    for option in state_dropdown.find_all("option"):
        if option.text.strip().upper() == state.upper():
            state_value = option['value']
            break

    if not state_value:
        print(f"State '{state}' not found in dropdown options!")
        return None, None

    # Submit form to select the state
    form_data = {
        "__VIEWSTATE": viewstate,
        "__EVENTVALIDATION": eventvalidation,
        "ctl00$ctl00$MainContent$searchMainContent$ctl01$ctl00$cboStates": state_value,
        "ctl00$ctl00$MainContent$searchMainContent$ctl01$ctl00$btnChangeCounty": "Go"
    }

    post_response = session.post(BASE_URL, data=form_data)
    if post_response.status_code != 200:
        print("Failed to select state.")
        return None, None

    print(f"State '{state}' selected successfully.")

    # Extract new hidden fields from response
    soup = BeautifulSoup(post_response.text, 'html.parser')
    new_viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
    new_eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]
    
    return new_viewstate, new_eventvalidation

# Function to select county
def select_county(session, county, viewstate, eventvalidation):
    """Select a county without reloading the page before"""
    response = session.get(BASE_URL)

    if response.status_code != 200:
        print("Failed to load the county selection page.")
        return False

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract hidden fields for form submission
    viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
    eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]

    # Find correct county value from dropdown
    county_dropdown = soup.find("select", {"id": "MainContent_searchMainContent_ctl01_ctl00_cboCounties"})
    county_value = None
    for option in county_dropdown.find_all("option"):
        if option.text.strip().upper() == county.upper():
            county_value = option['value']
            break

    if not county_value:
        print(f"County '{county}' not found in dropdown options!")
        return False

    # Submit form to select the county
    form_data = {
        "__VIEWSTATE": viewstate,
        "__EVENTVALIDATION": eventvalidation,
        "ctl00$ctl00$MainContent$searchMainContent$ctl01$ctl00$cboCounties": county_value,
        "ctl00$ctl00$MainContent$searchMainContent$ctl01$ctl00$btnChangeCounty": "Go"
    }

    post_response = session.post(BASE_URL, data=form_data)
    if post_response.status_code != 200:
        print("Failed to select county.")
        return False

    print(f"County '{county}' selected successfully.")
    return True
# Function to accept the disclaimer and navigate to the search page
def accept_disclaimer(session):
    disclaimer_url = f"{BASE_URL}/Disclaimer.aspx?RU=%2FIntroduction.aspx"
    
    response = session.get(disclaimer_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        form_action = soup.find("form")["action"]

        form_data = {
            "ctl00$ctl00$MainContent$searchMainContent$ctl01$btnAccept": "Yes, I Accept"
        }

        post_response = session.post(f"{BASE_URL}{form_action}", data=form_data)
        if post_response.status_code == 200:
            print("Disclaimer accepted. Redirecting to search page...")
            
            # After accepting the disclaimer, we now follow the search link.
            search_url = f"{BASE_URL}/Search.aspx"
            response = session.get(search_url)
            if response.status_code == 200:
                print("Search page loaded successfully.")
                return True
            else:
                print("Failed to load search page.")
                return False
        else:
            print("Failed to accept disclaimer.")
            return False
    return False

# Function to set up the search form
def setup_search(session, state, county, start_date, end_date):
    search_url = f"{BASE_URL}/Search.aspx"
    
    response = session.get(search_url)
    if response.status_code != 200:
        print("Failed to load search page.")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract hidden fields for form submission
    viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
    eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]
    
    # Correct value for 'Lien' document group
    lien_value = "365|LIEN"
    
    form_data = {
        "__VIEWSTATE": viewstate,
        "__EVENTVALIDATION": eventvalidation,
        "ctl00$ctl00$MainContent$searchMainContent$ctl00$cboDocumentType": lien_value,
        "ctl00$ctl00$MainContent$searchMainContent$ctl00$tbDateStart": start_date,
        "ctl00$ctl00$MainContent$searchMainContent$ctl00$tbDateEnd": end_date,
        "ctl00$ctl00$MainContent$searchMainContent$ctl00$btnSearchDocuments": "Execute Search"
    }
    
    response = session.post(search_url, data=form_data)
    if response.status_code == 200:
        print("Search executed successfully.")
        return response.text
    else:
        print("Failed to execute search.")
        return None

# Function to parse results and download files
def get_results_and_download(soup,session, output_folder, start_date, end_date):
    print("Parsing search results...")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    parent_table = soup.find("table", id="tableMain")
    if parent_table:
        print("Parent table found")

        table_content = parent_table.find("td", id="tableMain_Content")
        if table_content:
            print("Found tableMain_Content td")
            print(table_content)

            main_div = table_content.find("div", class_="main")
            if main_div:
                print("Found div.main")
                print(main_div)
                print_results_div = main_div.find("div", id="PrintResults")
                print(print_results_div)
                if print_results_div:
                    print("Found PrintResults div")

                    results_table = print_results_div.find("table", class_="Results")
                    if results_table:
                        print("Found results table")
                        rows = results_table.find_all("tr", class_=["results-data-row", "results-data-row listitem-background-color2", "results-data-row listitem-background-color1"])

                        # Convert start_date and end_date to datetime.date objects
                        try:
                            start_date_obj = datetime.strptime(start_date, "%m-%d-%Y").date()
                            end_date_obj = datetime.strptime(end_date, "%m-%d-%Y").date()
                        except ValueError:
                            print(f"Invalid date format for start_date or end_date. Please use MM-DD-YYYY.")
                            return

                        # Prepare to write results and image links
                        with open(f"{output_folder}/search_results.csv", mode='w', newline='', encoding='utf-8') as file:
                            writer = csv.writer(file)
                            writer.writerow(["Item#", "Document ID#", "Recording Date", "Document Type", "Document Name", "Name Type", "Document", "Page Count"])
                            for row in rows:
                                cells = row.find_all("td")
                                if len(cells) < 6:
                                    print("Skipping row with insufficient columns")
                                    continue

                                item_number = cells[0].text.strip()
                                document_id = cells[1].text.strip()
                                recording_date = cells[2].text.strip()
                                document_type = cells[3].text.strip()
                                document_name = cells[4].text.strip()
                                name_type = cells[5].text.strip()

                                # Extract hyperlink for document ID
                                document_link = ""
                                if cells[1].find("a"):
                                    document_link = cells[1].find("a")["href"]

                                page_count = get_page_count( session,document_link) if document_link else "N/A"

                                try:
                                    # Try parsing with time
                                    record_date_obj = datetime.strptime(recording_date, "%m-%d-%Y %I:%M:%S %p").date()
                                except ValueError:
                                    try:
                                        # Try parsing without time
                                        record_date_obj = datetime.strptime(recording_date, "%m-%d-%Y").date()
                                    except ValueError:
                                        print(f"Skipping invalid date: {recording_date}")
                                        continue  # Skip this row if both fail

                                # Compare the record date with the start and end dates
                                if start_date_obj <= record_date_obj <= end_date_obj:
                                    writer.writerow([item_number, document_id, recording_date, document_type, document_name, name_type, document_link, page_count])
                                    print(f"Extracted: {item_number}, {document_id}, {recording_date}, {document_type}, {document_name}, {name_type}, {document_link}, {page_count}")
                                
                                if document_link and page_count.isdigit():
                                        download_images(session, document_id, document_link, int(page_count), output_folder)
                    else:
                        print("Results table not found inside PrintResults div.")
                else:
                    print("PrintResults div not found inside div.main.")
            else:
                print("div.main not found inside tableMain_Content.")
        else:
            print("tableMain_Content td not found.")

def get_page_count(session, document_link):
    base_url = "https://www.thecountyrecorder.com/"
    full_url = base_url + document_link
    response = session.get(full_url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Check for "View Image" button presence
        view_image_button = soup.find("input", id="MainContent_searchMainContent_ctl00_btnViewImage")
        if not view_image_button:
            print("No 'View Image' button found. Skipping image extraction for this document.")
            return "N/A"

        # Extract page count
        page_count_input = soup.find("input", id="MainContent_searchMainContent_ctl00_tbPageCount")
        if page_count_input and "value" in page_count_input.attrs:
            print(f"Found page count input: {page_count_input['value']}")
            return page_count_input["value"].strip()
        
    return "N/A"

def download_images(session, document_id, link, page_count, output_folder):
    x_value = link.split("?")[-1]
    base_url = "https://www.thecountyrecorder.com"
    
    # Create output directory if it doesn't exist
    doc_folder = os.path.join(output_folder, document_id)
    os.makedirs(doc_folder, exist_ok=True)
    
    for page_num in range(1, page_count + 1):
        image_page_url = f"{base_url}/Image.aspx?{x_value}&PN={page_num}"
        response = session.get(image_page_url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            image_tag = soup.find("img", {"id": "MainContent_searchMainContent_ctl00_Image2"})
            
            if image_tag and "src" in image_tag.attrs:
                image_url = f"{base_url}/{image_tag['src']}"
                image_response = session.get(image_url, stream=True)
                
                if image_response.status_code == 200 and 'image' in image_response.headers.get('Content-Type', ''):
                    file_name = os.path.join(doc_folder, f"{document_id}_page_{page_num}.jpg")
                    with open(file_name, 'wb') as file:
                        for chunk in image_response.iter_content(1024):
                            file.write(chunk)
                    print(f"Downloaded {file_name}")
                else:
                    print(f"Failed to download image from {image_url} or received non-image content.")
            else:
                print(f"No image found on page {page_num}")
        else:
            print(f"Failed to load image page {image_page_url}")

# Function to download files
def download_files(document_id, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    file_url = f"{BASE_URL}/Document.aspx?DK={document_id}"

    response = requests.get(file_url)
    if response.status_code == 200:
        file_name = os.path.join(output_folder, f"{document_id}.pdf")
        with open(file_name, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {file_name}")
    else:
        print(f"Failed to download {file_url}")

# Main scraping function
def scrape(state, county, start_date, end_date, output_folder):
    
    session = requests.Session()
    session.cookies.clear()  # Optionally clear cookies manually

    if not select_state(session, state,):
        return
    if not select_county(session, county):
        return
    if not accept_disclaimer(session):
        return
    
    search_page_html = setup_search(session, state, county, start_date, end_date)
    
    if search_page_html:
        soup = BeautifulSoup(search_page_html, 'html.parser')
        get_results_and_download(soup, session,output_folder, start_date, end_date)

# User input
def user_input():
    state = "COLORADO"
    county = "WASHINGTON"
    start_date = "01-01-2020"
    end_date = "01-01-2022"
    output_folder = "output"
    return state, county, start_date, end_date, output_folder


# Main entry point
if __name__ == "__main__":
    state, county, start_date, end_date, output_folder = user_input()
    scrape(state, county, start_date, end_date, output_folder)
