# Redirect URL Mapper • NUR® Digital Marketing

## Overview

This tool is designed to streamline the process of mapping redirects during website migrations by comparing crawls of legacy and new URLs. It automatically identifies and matches URLs based on similarity in their paths, slugs, titles, H1, and H2 tags.

### Key Features
- Automatic URL matching based on various page elements (URL, slugs, titles, H1, H2).
- Multiple match sheets generated, including: URL match, slug match, title match, H1 match, and H2 match.
- Support for uploading `.xlsx` files directly from Screaming Frog or via [advertools spider](https://advertools.readthedocs.io/en/master/advertools.spider.html).
- Simple user interface for uploading crawls and downloading the redirect mapping in Excel format.
- Significant time savings in the manual redirect mapping process, estimated up to 60%.

## How to Use
1. Upload two `.xlsx` files: one containing the crawl of legacy URLs and another for the new URLs.
2. The tool will process and match the URLs based on their paths, slugs, titles, H1, and H2 tags.
3. After processing, you can download an Excel file that includes the redirect mappings.

## Requirements
- Python 3.x
- Libraries: `advertools`, `pandas`, `streamlit`, `openpyxl`, `polyfuzz`
- Both uploaded files should include the following columns: `Address`, `Title 1`, `H1-1`, `H2-1`

## Installation

To run the tool locally:

```bash
git clone https://github.com/yourusername/redirect-url-mapper.git
cd redirect-url-mapper
pip install -r requirements.txt
streamlit run app.py
```
