import time, os, csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from fake_useragent import UserAgent
from selenium.webdriver.common.action_chains import ActionChains
from os.path import join, dirname
from dotenv import load_dotenv
import xlsxwriter
from threading import Thread
import logging
from logging.handlers import RotatingFileHandler
import platform

from bs4 import BeautifulSoup
import requests, sys


cur_path = dirname(__file__)
root_path = cur_path[:cur_path.rfind(os.path.sep)]
# root_path = root_path[:root_path.rfind(os.path.sep)]
load_dotenv(join(root_path, '.env'))
log_file_size = 20
formatter = logging.Formatter('%(asctime)s    %(message)s')
scrape_status = ""


def my_logging(log, msg):
    global root_path

    log.propagate = True
    fileh = RotatingFileHandler(join(root_path, "log", "reydonsports.log"), mode='a', maxBytes=log_file_size*1024, backupCount=2, encoding='utf-8', delay=0)
    # ('logs/' + f_name + '.log', 'a')
    fileh.setFormatter(formatter)
    for hdlr in log.handlers[:]:  # remove all old handlers
        log.removeHandler(hdlr)
    log.addHandler(fileh)
    log.critical(msg)
    log.propagate = False


class RDS_Category_Thread(Thread):
 
    def __init__(self, stock_scrape):
        Thread.__init__(self)
        self.stock_scrape = stock_scrape
        self.log = logging.getLogger("a")  # root logger
        self.status = ""
        
         
    def run(self):
        now = datetime.now()
        mail_address = os.environ.get('RDS_LOGIN_ID')
        mail_password = os.environ.get('RDS_PASSWORD')

        try:
            self.main_loop(mail_address, mail_password, self.stock_scrape)
        except Exception as e:
            # driver.save_screenshot(datetime.now().strftime("screenshot_%Y%m%d_%H%M%S_%f.png"))
            self.status_publishing(e)
        finally:
            pass


    def main_loop(self, user_email, user_password, stock_scrape=0):
        BASE_URL = "https://www.reydonsports.com"        
        category_link_list = []
        products_link_list = []
        products_dict = {}
        user_email = os.environ.get('RDS_LOGIN_ID')
        user_password = os.environ.get('RDS_PASSWORD')

        fields = ['SKU', 'Name', 'Description', 'Trade Price', 'SRP Price', 'Price', 'Stock', 'URL', 'Image', 'Category', 'Commodity Code', 'Barcode', 'Shipping Dimensions', 'Shipping Weight', 'Country of Origin', 'Colour', 'Length']
        if stock_scrape == 1: fields = ['SKU', 'Name', 'stock']

        # # generate .xlsx file name
        # timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
        # xlsfile_name = 'products-' + timestamp + '.xlsx'
        # if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '.xlsx'
        # xlsfile_name = join(root_path, "xls", "reydonsports", xlsfile_name)
        # print(xlsfile_name)

        # workbook = xlsxwriter.Workbook(xlsfile_name)
        # worksheet = workbook.add_worksheet()

        with requests.Session() as s:
            # Get CSRF_TOKEN
            page = s.get("https://www.reydonsports.com")
            soup = BeautifulSoup(page.content, 'html.parser')
            script_snippet = str(soup.find("script"))
            script_snippet = script_snippet[script_snippet.find('csrf_token'):]
            script_snippet = script_snippet[script_snippet.find('"') + 1:]
            csrf_token = script_snippet[:script_snippet.find('"')]
            
            p = s.post("https://www.reydonsports.com/web/login", data={
                "login": user_email,
                "password": user_password,
                "csrf_token": csrf_token
            })

            # Get SESSION_ID
            cookie = p.headers["Set-Cookie"]
            cookie = cookie[cookie.find("session_id"):]
            cookie = cookie[cookie.find("=") + 1:]
            session_id = cookie[:cookie.find(";")]

            # Set HEADER
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'cookie': 'frontend_lang=en_GB; session_id=e065a7444d4a835d3a1969bd5ee64520ed8438d7; _ga=GA1.2.248003462.1624860338; _gid=GA1.2.482944600.1624860338'
            }


    # START --- GET PRODUCT LINK --- 

            products_url_txt = open("reydonsports_products_url.txt","w")
            base_page = s.get('https://www.reydonsports.com/shop')
            soup = BeautifulSoup(base_page.content, 'html.parser')
            for dropdown in soup.select(".dropdown ul")[3:7]:
                print(" ===============  dropdown = ")
                # print(dropdown)
                for category in dropdown.select("li a"):
                    print(category['href'])
                    category_link_list.append(category['href'])
            
            # Get Products Links
            for category_link in category_link_list:
                link = category_link
                if link[0] == "/": 
                    link = BASE_URL + link
                page = s.get(link, headers=headers)
                soup = BeautifulSoup(page.content, 'html.parser')
                page_num = 1
                while True:
                    self.status_publishing("Category Link : " + category_link + ", Page number : " + str(page_num))
                    products = soup.find_all('div', attrs={'class':'oe_product oe_shop_left oe_product_cart'})
                    for product in products:
                        a = product.find('a', attrs={'itemprop': 'url'})
                        products_link_list.append(a['href'])
                        products_url_txt.write(a['href'] + "\n")

                    next_btn = soup.find("a", string="Next")
                    if next_btn and next_btn['href'] != "":
                        page_num += 1
                        if link.find("?") > -1:
                            link_1 = link[:link.find("?")]
                            page = s.get(link_1 + "/page/" + str(page_num), headers=headers)
                        else:
                            page = s.get(link + "/page/" + str(page_num), headers=headers)
                        soup = BeautifulSoup(page.content, 'html.parser')
                    else:
                        break

            products_url_txt.close()

    # END --- GET PRODUCT LINK ---   
            self.status_publishing("ended")
            time.sleep(10)
            sys.exit()
            
        
    def status_publishing(self,text) :
        global scrape_status

        scrape_status = text
        self.status = text
        print(text)
