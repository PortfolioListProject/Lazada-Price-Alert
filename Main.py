import requests
import smtplib
import time
from bs4 import BeautifulSoup

# Example:
# url = 'https://www.lazada.com.my/products/pdp-i4121340569-s23343625071.html'

url = 'YOUR URL HERE'  

# You can search up your user agent by searching "my user agent" in Google and copying the result
# headers = {
# "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
# }

headers = {
    "User-Agent": "YOUR USER AGENT HERE"  
}


def check_price():
    page = requests.get(url, headers=headers)

    soup = BeautifulSoup(page.content, 'html.parser')

    title = soup.find('title').get_text(strip=True)

    price_element = soup.find('meta', property='product:price:amount')

    if price_element:
        price = float(price_element.get('content'))
    else:
        price = None

    if price is not None and price < 1.70:
        send_mail(title, price)


def send_mail(title, price):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()

    server.login('yourname@gmail.com', 'your-app-password')

    subject = 'Price fell down!'

    body = f'The price of the product "{title}" has dropped to RM{price}. Check it out at {url}'

    msg = f'Subject: {subject}\n\n{body}'

    server.sendmail(
        'yourname@gmail.com',
        'recipient@gmail.com',
        msg
    )

    print('Email has been sent!')

    server.quit()

while(True):
    check_price()
    time.sleep(3600)  







