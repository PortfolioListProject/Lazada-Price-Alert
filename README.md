# Lazada-Price-Alert
Python web scraper that monitors the price of a Lazada Malaysia product and sends an email notification if price goes down

## Requirement
pip install requests beautifulsoup4

## Configuration you need to do

url = 'YOUR URL'

headers = {"User-Agent": 'YOUR USER AGENT'}

server.login('YOUR_GMAIL', 'YOUR_APP_PASSWORD')

server.sendmail(
    'YOUR_GMAIL',
    'YOUR_RECEIVING_EMAIL',
    msg
)

you can change the price at line 32 to alert you
