import pdfplumber
import pandas as pd
import io

def extract_tables_from_pdf(file_bytes: bytes) -> pd.DataFrame:
    """
    Extracts structured tables from a digital PDF file into a clean pandas DataFrame.
    """
    all_rows = []
    headers = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            # Extract structured tables from the page
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue

                # The first valid table header found becomes the global header
                if not headers:
                    headers = [str(c).strip() if c else f"col_{i}" for i, c in enumerate(table[0])]
                    data_rows = table[1:]
                else:
                    data_rows = table

                for row in data_rows:
                    # Pad or truncate row to match header length
                    cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    if len(cleaned_row) < len(headers):
                        cleaned_row.extend([""] * (len(headers) - len(cleaned_row)))
                    all_rows.append(cleaned_row[:len(headers)])

    if not headers or not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=headers)
    # Drop completely blank rows
    df = df.dropna(how='all')
    return df