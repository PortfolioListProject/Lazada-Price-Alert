import queue
import re
import smtplib
import threading
import tkinter as tk
from email.message import EmailMessage
from tkinter import messagebox, ttk
 
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright
 
PRICE_SELECTOR = ".pdp-v2-product-price-content-salePrice-amount"
BLOCK_MARKERS = ("baxia", "punish", "captcha", "x5secdata")
 
stop_event = threading.Event()
status_queue = queue.Queue()
worker = None
 
def set_status(text):
    """Thread-safe status update: worker threads put text on a queue,
    the Tk main thread reads it in poll_status()."""
    print(text)
    status_queue.put(text)
 
 
def parse_price(text):
    match = re.search(r"\d[\d,]*\.?\d*", text or "")
    if not match:
        return None
    return float(match.group().replace(",", ""))
 
 
def fetch_product(page, url):
    """Load the page in a real browser and return (title, price, error)."""
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    title = page.title() or "Unknown Product"
 
    try:
        page.wait_for_selector(PRICE_SELECTOR, timeout=20000)
        price = parse_price(page.inner_text(PRICE_SELECTOR))
        if price is not None:
            return title, price, None
    except PlaywrightTimeout:
        pass
 
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", property="product:price:amount")
    if meta and meta.get("content"):
        price = parse_price(meta["content"])
        if price is not None:
            return title, price, None
 
    lowered = html.lower()
    if any(marker in lowered for marker in BLOCK_MARKERS):
        return title, None, "Blocked by Lazada anti-bot page (try a visible browser window)"
    return title, None, "Price element not found"
 
 
def send_mail(title, price, url, sender, password, recipient):
    msg = EmailMessage()
    msg["Subject"] = "Price fell down!"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f'The price of the product "{title}" has dropped to RM{price:.2f}.\n\n'
        f"Check it out at {url}"
    )
 
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
 
 
def launch_browser(p, browser_name):
    if browser_name in ("msedge", "chrome"):
        return p.chromium.launch(channel=browser_name, headless=False)
    if browser_name == "firefox":
        return p.firefox.launch(headless=False)
    return p.chromium.launch(headless=False)
 
def monitor(settings):
    """Runs in a background thread. Playwright's sync API must be started
    and used inside the same thread, so everything happens here."""
    last_notified_price = None
 
    try:
        with sync_playwright() as p:
            browser = launch_browser(p, settings["browser"])
            page = browser.new_page()
 
            while not stop_event.is_set():
                try:
                    title, price, error = fetch_product(page, settings["url"])
 
                    if price is None:
                        set_status(f"Could not read price: {error}")
                    else:
                        set_status(f"Current price: RM{price:.2f}")
 
                        if price < settings["target"]:
                            if price != last_notified_price:
                                send_mail(
                                    title,
                                    price,
                                    settings["url"],
                                    settings["sender"],
                                    settings["password"],
                                    settings["recipient"],
                                )
                                last_notified_price = price
                                set_status(f"Email sent! Price: RM{price:.2f}")
                        else:
                            last_notified_price = None
 
                except Exception as e:
                    set_status(f"Error: {e}")
 
                stop_event.wait(settings["interval"] * 60)
 
            browser.close()
 
    except Exception as e:
        set_status(f"Browser error: {e}")
 
    set_status("Monitoring stopped.")
 
def start_monitoring():
    global worker
 
    if worker is not None and worker.is_alive():
        return
 
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Missing URL", "Please enter a product URL.")
        return
 
    try:
        target = float(price_entry.get())
    except ValueError:
        messagebox.showerror("Invalid Price", "Please enter a valid target price.")
        return
 
    try:
        interval = float(interval_entry.get())
        if interval <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid Interval", "Enter the check interval in minutes (e.g. 60).")
        return
 
    settings = {
        "url": url,
        "target": target,
        "interval": interval,
        "sender": email_entry.get().strip(),
        "password": password_entry.get(),
        "recipient": recipient_entry.get().strip(),
        "browser": browser_box.get(),
    }
 
    stop_event.clear()
    set_status("Monitoring started...")
    worker = threading.Thread(target=monitor, args=(settings,), daemon=True)
    worker.start()
 
 
def stop_monitoring():
    stop_event.set()
    set_status("Stopping...")
 
 
def poll_status():
    try:
        while True:
            status_label.config(text=status_queue.get_nowait())
    except queue.Empty:
        pass
    window.after(200, poll_status)
 
 
def on_close():
    stop_event.set()
    if worker is not None and worker.is_alive():
        worker.join(timeout=5)  
    window.destroy()
 
 
#Layout
 
window = tk.Tk()
window.title("Price Alert")
window.geometry("550x620")
 
tk.Label(window, text="Product Price Alert", font=("Arial", 20, "bold")).pack(pady=15)
 
 
def add_field(label, width=50, show=None):
    tk.Label(window, text=label).pack()
    entry = tk.Entry(window, width=width, show=show)
    entry.pack(pady=4)
    return entry
 
 
url_entry = add_field("Product URL:", width=65)
price_entry = add_field("Target Price (RM):", width=30)
interval_entry = add_field("Check every (minutes):", width=30)
interval_entry.insert(0, "60")
email_entry = add_field("Gmail Address:", width=40)
password_entry = add_field("Gmail App Password:", width=40, show="*")
recipient_entry = add_field("Recipient Email:", width=40)
 
tk.Label(window, text="Browser:").pack()
browser_box = ttk.Combobox(
    window,
    values=["msedge", "chrome", "chromium", "firefox"],
    state="readonly",
    width=20,
)
browser_box.set("msedge")
browser_box.pack(pady=4)

 
button_frame = tk.Frame(window)
button_frame.pack(pady=15)
 
tk.Button(button_frame, text="Start Monitoring", command=start_monitoring, width=18).grid(
    row=0, column=0, padx=10
)
tk.Button(button_frame, text="Stop Monitoring", command=stop_monitoring, width=18).grid(
    row=0, column=1, padx=10
)
 
status_label = tk.Label(window, text="Waiting...", font=("Arial", 12), wraplength=500)
status_label.pack(pady=10)
 
window.protocol("WM_DELETE_WINDOW", on_close)
poll_status()
window.mainloop()









