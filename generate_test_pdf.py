import requests
def download_test_pdf():
    # Download a sample 5-page PDF for testing
    url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    r = requests.get(url)
    with open("test_upload.pdf", "wb") as f:
        f.write(r.content)
    print("test_upload.pdf created")

download_test_pdf()
