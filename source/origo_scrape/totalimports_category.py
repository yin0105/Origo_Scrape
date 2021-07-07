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
load_dotenv(join(root_path, '.env'))
log_file_size = 20
formatter = logging.Formatter('%(asctime)s    %(message)s')
scrape_status = ""


def my_logging(log, msg):
    global root_path

    log.propagate = True
    fileh = RotatingFileHandler(join(root_path, "log", "TotalImports.log"), mode='a', maxBytes=log_file_size*1024, backupCount=2, encoding='utf-8', delay=0)
    # ('logs/' + f_name + '.log', 'a')
    fileh.setFormatter(formatter)
    for hdlr in log.handlers[:]:  # remove all old handlers
        log.removeHandler(hdlr)
    log.addHandler(fileh)
    log.critical(msg)
    log.propagate = False


class TotalImports_Category_Thread(Thread):
 
    def __init__(self, stock_scrape):
        Thread.__init__(self)
        self.stock_scrape = stock_scrape
        self.log = logging.getLogger("a")  # root logger
        self.status = ""
        
         
    def run(self):
        now = datetime.now()
        mail_address = os.environ.get('TOTALIMPORTS_LOGIN_ID')
        mail_password = os.environ.get('TOTALIMPORTS_PASSWORD')

        try:
            self.main_loop(mail_address, mail_password, self.stock_scrape)
        except Exception as e:
            # driver.save_screenshot(datetime.now().strftime("screenshot_%Y%m%d_%H%M%S_%f.png"))
            self.status_publishing(e)
        finally:
            pass


    def main_loop(self, user_email, user_password, stock_scrape=0):
        print("main_loop()")
        BASE_URL = "https://www.totalimports.ie"        
        category_link_list = []

        # fields = ['SKU', 'Name', 'Description', 'Trade Price', 'SRP Price', 'Price', 'Stock', 'URL', 'Image', 'Category', 'Commodity Code', 'Barcode', 'Shipping Dimensions', 'Shipping Weight', 'Country of Origin', 'Colour', 'Length']
        # if stock_scrape == 1: fields = ['SKU', 'Name', 'stock']

        with requests.Session() as s:
            p = s.post("https://www.totalimports.ie/signin.aspx", data={
                "ctl00$ctl06$extCollapseMinicart_ClientState": "true",
                "ctl00$PageContent$ctl00$ctrlLogin$UserName": user_email,
                "ctl00$PageContent$ctl00$ctrlLogin$Password": user_password,
                "ctl00$PageContent$ctl00$ctrlLogin$LoginButton": "Login",
            })

            # Get SESSION_ID
            cookie = p.headers["Set-Cookie"]
            
            session_id = cookie[cookie.find("ASP.NET_SessionId"):]
            session_id = session_id[session_id.find("=") + 1:]
            session_id = session_id[:session_id.find(";")]

            anonymous = cookie[cookie.find(".ASPXANONYMOUS"):]
            anonymous = anonymous[anonymous.find("=") + 1:]
            anonymous = anonymous[:anonymous.find(";")]

            # Set HEADER
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'cookie': 'Cookie: ASP.NET_SessionId=' + session_id + '; .ASPXANONYMOUS=' + anonymous + '; __utmc=77576080; \
                    __utmz=77576080.1625304625.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); cb-enabled=enabled; \
                    __utma=77576080.904269643.1625304625.1625565324.1625572632.3; __utmt=1; __utmb=77576080.10.10.1625572632;',
            }


    # START --- GET PRODUCT LINK --- 

            products_url_txt = open("totalimports_products_url.txt","w")
            base_page = s.get('https://www.totalimports.ie/default.aspx')
            soup = BeautifulSoup(base_page.content, 'html.parser')
            for main_category in soup.select("#Categories ul li a"):
                category_link_list.append({"name": main_category.getText(), "href": main_category['href']})
            print(category_link_list)
            
            # Get Products Links
            for category_link in category_link_list:
                link = category_link["href"]
                if link[0] == "/": 
                    link = BASE_URL + link
                page = s.get(link, headers=headers)
                soup = BeautifulSoup(page.content, 'html.parser')
                
                sub_categories = soup.select(".subentityResult")
                for sub_category in sub_categories:
                    href = sub_category.select("a")[1]["href"]
                    name = sub_category.select("a")[1].select_one("span").getText()
                    category_link_list.append({"name": category_link["name"] + " / " + name, "href": href})

                page_num = 1
                while True:
                    self.status_publishing("Category Link : " + category_link["name"] + ", Page number : " + str(page_num))
                    is_last = False
                    for product in soup.select(".productResult"):
                        product_link = product.select('div h2 a')[0]["href"]
                        print(product_link)
                        products_url_txt.write(category_link["name"] + "::" + product_link + "\n")

                    next_btn = soup.find_all("li", attrs={'class':'pagingPreviousNext'}, string="Next »")
                    print("next_btn = ", next_btn)
                    if len(next_btn) == 0 or next_btn[0]["class"][-1] == "pagingDisabled": break
                
                    page_num += 1
                    page = s.get(link + "?pagenum=" + str(page_num), headers=headers)
                    soup = BeautifulSoup(page.content, 'html.parser')

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
