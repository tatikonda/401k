import os
import re
import requests
import xml.etree.ElementTree as ET
import csv
import pdfplumber
from argparse import ArgumentParser
import zipfile
import sys

def get_params():
    parser = ArgumentParser(prog='senator.py', usage='Provide senator last name and year', description='A script to get senator trades for that year')
    parser.add_argument("-y", "--year", action="store")
    parser.add_argument("-l", "--last_name", action="store")
    params = parser.parse_args(sys.argv[1:])
    return params

# Function to download the XML file from a ZIP archive based on the year
def download_and_extract_xml(year="2023", output_dir="xml_files"):
    zip_url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
    zip_filename = os.path.join(output_dir, f"{year}FD.zip")
    xml_filename = os.path.join(output_dir, f"{year}FD.xml")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Download the ZIP file
        print(f"Downloading {zip_url}...")
        response = requests.get(zip_url)
        response.raise_for_status()  # Raise error for failed requests

        # Save the ZIP file
        with open(zip_filename, "wb") as zip_file:
            zip_file.write(response.content)
        print(f"Downloaded ZIP file: {zip_filename}")

        # Extract the XML file from the ZIP archive
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall(output_dir)  # Extract all contents to the output directory
        print(f"Extracted XML file: {xml_filename}")

        return xml_filename  # Return the path to the extracted XML file

    except requests.exceptions.RequestException as e:
        print(f"Failed to download {zip_url}: {e}")
        return None
    
# Function to parse XML and download PDFs with a parameterized year
def download_pdfs_from_xml(xml_file, output_dir, member_last_name=None, year="2024"):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for member in root.findall(".//Member"):
        last_name = member.find("Last").text
        doc_id = member.find("DocID").text

        # If a specific member is provided, skip others
        if member_last_name and last_name.lower() != member_last_name.lower():
            continue

        # Parameterized URL with year
        pdf_url = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"
        output_file = os.path.join(output_dir, f"{last_name}_{doc_id}.pdf")

        try:
            response = requests.get(pdf_url)
            response.raise_for_status()  # Raise error for failed requests
            with open(output_file, "wb") as file:
                file.write(response.content)
            print(f"Downloaded: {output_file}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {pdf_url}: {e}")

def extract_text_from_pdf_with_pdfplumber(pdf_path):
    extracted_text = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_text += page.extract_text()  # Extracts text from each page
    return extracted_text

def clean_extracted_text(text):
    # First, replace unwanted characters (except for newlines) with a placeholder
    # Keep \n (newlines) intact and replace other control characters and non-printable characters
    text = re.sub(r'[^\x20-\x7E\n]', '', text)  # Remove non-ASCII printable characters except newline
    
    # Then, normalize excessive spaces to a single space (preserve newlines)
    text = re.sub(r'[ \t]+', ' ', text)  # Replace multiple spaces and tabs with a single space
    
    # Optional: Clean up unnecessary spaces around newlines, if required
    text = re.sub(r'\n+', '\n', text)  # Replace multiple newlines with a single newline
    
    return text

# Function to parse the data
def parse_transactions(data):
    # Split the input text by lines
    lines = data.split("\n")
    transactions = []
    
    # Temporary variables to store data
    ticker = None
    transaction_type = None
    transaction_date = None
    description = None
    
    # Iterate over each line in the data
    for line in lines:
        # Strip line to avoid leading/trailing spaces causing issues
        line = line.strip()
        
        # Debugging output for each line being processed
        #print(f"Processing line: {line}")

        # Step 1: Extract Ticker symbol from parentheses (e.g., (AVGO))
        ticker_match = re.search(r'\((\w+)\)', line)
        if ticker_match:
            ticker = ticker_match.group(1)
            #print(ticker)

        # Step 2: Extract Transaction Type (P or S)
        if 'P' in line or 'S' in line:
            if 'P' in line:
                transaction_type = 'P'
            elif 'S' in line:
                transaction_type = 'S'
        
        # Step 3: Extract Date in MM/DD/YYYY format
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
        if date_match:
            transaction_date = date_match.group(1)
        #print(transaction_date)
        # Step 4: Extract Description starting with D: till the end of the line
        if 'D:' or 'DESCRIPTION:' or 'S O:' in line.upper():
            print(f"Processing line: {line}")
            description_match = re.search(r'D:\s*(.*)|DESCRIPTION:\s*(.*)|O:\s*(.*)', line)
            
            if description_match:
                description = description_match.group(0).strip()
            #elif description_match is None:
            #    description = "NA"

                # Now, append the extracted values to the transaction list
                if ticker and transaction_type and transaction_date and description:
                    transaction_data = {
                        "asset": ticker,
                        "transaction_type": transaction_type,
                        "transaction_date": transaction_date,
                        "description": description
                    }
                    #print(f"Parsed Transaction: {transaction_data}")
                    transactions.append(transaction_data)

                    # Reset temporary variables to avoid reusing previous transaction data
                    ticker = transaction_type = transaction_date = description = None

    return transactions


# Function to process PDFs and extract transactions
def process_pdfs_and_extract_transactions(pdf_dir, output_file):
    all_transactions = []
    for pdf_file in os.listdir(pdf_dir):
        if pdf_file.endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, pdf_file)
            print(f"Processing {pdf_path}...")
            text = extract_text_from_pdf_with_pdfplumber(pdf_path)
            clean_data = clean_extracted_text(text)
            #print(clean_data)
            if clean_data:
                parsed_transactions = parse_transactions(clean_data)
                for transaction in parsed_transactions:
                    print(transaction)
                    transaction["source_file"] = pdf_file  # Add source file info
                    all_transactions.append(transaction)

    # Save all transactions to a CSV file
    save_transactions_to_csv(all_transactions, output_file)

# Function to save transactions to CSV
def save_transactions_to_csv(transactions, output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["asset", "transaction_type", "transaction_date", "description", "source_file"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)
    print(f"Transactions saved to {output_file}")

# main

# Assign the params
params = get_params()
year=params.year
last_name=params.last_name

pdf_dir = "pdf_downloads"  # Directory for downloaded PDFs
output_file = "transactions.csv"  # Output CSV file for transactions

print("Downloading and extracting XML...")
xml_file = download_and_extract_xml(year=year)

print("Downloading PDFs...")
download_pdfs_from_xml(xml_file, pdf_dir, last_name, year)

print("Extracting transactions from PDFs...")
process_pdfs_and_extract_transactions(pdf_dir, output_file)
