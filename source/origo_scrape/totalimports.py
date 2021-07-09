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
import platform, openpyxl

from bs4 import BeautifulSoup
import requests, sys, re


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
    fileh = RotatingFileHandler(join(root_path, "log", "totalimports.log"), mode='a', maxBytes=log_file_size*1024, backupCount=2, encoding='utf-8', delay=0)
    # ('logs/' + f_name + '.log', 'a')
    fileh.setFormatter(formatter)
    for hdlr in log.handlers[:]:  # remove all old handlers
        log.removeHandler(hdlr)
    log.addHandler(fileh)
    log.critical(msg)
    log.propagate = False


class TotalImports_Thread(Thread):
 
    def __init__(self, thread_index, start_index, end_index, stock_scrape):
        Thread.__init__(self)
        self.stock_scrape = stock_scrape
        self.start_index = start_index
        self.end_index = end_index
        self.thread_index = thread_index
        self.log = logging.getLogger("a")  # root logger
        self.status = ""

        # if thread_index == 0: self.added = 132
        # if thread_index == 2: self.added = 116
        # if thread_index == 4: self.added = 114
        # if thread_index == 5: self.added = 135
        # if thread_index == 8: self.added = 130
        # if thread_index == 9: self.added = 110


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
        BASE_URL = "https://www.totalimports.ie"        

        fields = ['SKU', 'Name', 'Category', 'Price', 'Stock', 'Weight', 'Description', 'URL', 'Image']
        if stock_scrape == 1: fields = ['SKU', 'Stock']

        # generate .xlsx file name
        # timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
        xlsfile_name = str(self.thread_index) + '-temp.xlsx'
        # if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '-' + str(self.thread_index) + '-temp.xlsx'
        xlsfile_name = join(root_path, "xls", "totalimports", xlsfile_name)
        print(xlsfile_name) 

        with requests.Session() as s:
            page = s.get('https://www.totalimports.ie/signin.aspx')
            soup = BeautifulSoup(page.content, 'html.parser')
            data = {}
            data["__VIEWSTATE"] = soup.select_one("#__VIEWSTATE")["value"]
            data["__EVENTVALIDATION"] = soup.select_one("#__EVENTVALIDATION")["value"]
            data["__EVENTTARGET"] = ""
            data["__EVENTARGUMENT"] = ""
            data["ctl00$ctl06$extCollapseMinicart_ClientState"] = "true"
            data["ctl00$PageContent$ctl00$ctrlLogin$UserName"] = user_email
            data["ctl00$PageContent$ctl00$ctrlLogin$Password"] = user_password
            data["ctl00$PageContent$ctl00$ctrlLogin$LoginButton"] = "Login"

            # Get SESSION_ID
            cookie = page.headers["Set-Cookie"]
            
            session_id = cookie[cookie.find("ASP.NET_SessionId"):]
            session_id = session_id[session_id.find("=") + 1:]
            session_id = session_id[:session_id.find(";")]

            anonymous = cookie[cookie.find(".ASPXANONYMOUS"):]
            anonymous = anonymous[anonymous.find("=") + 1:]
            anonymous = anonymous[:anonymous.find(";")]

            # Set HEADER
            headers = {
                'cookie': 'Cookie: ASP.NET_SessionId=' + session_id + '; .ASPXANONYMOUS=' + anonymous + '; __utmc=77576080; \
                    __utmz=77576080.1625304625.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); cb-enabled=enabled; \
                    __utma=77576080.904269643.1625304625.1625565324.1625572632.3; __utmt=1; __utmb=77576080.10.10.1625572632;',
                'Host': 'totalimports.ie',
                # 'Referer': 'http://totalimports.ie/c-42-microphone-amp-headsets.aspx',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            }

            
            p = s.post("https://www.totalimports.ie/signin.aspx", 
                data=data, headers=headers
            )

            products_url_txt = open("totalimports_products_url.txt","r")
            
            workbook = xlsxwriter.Workbook(xlsfile_name)
            worksheet = workbook.add_worksheet()
            i = -1  
            for head in fields:
                i += 1            
                worksheet.write(0, i, head)
            workbook.close()

            workbook = openpyxl.load_workbook(xlsfile_name)
            worksheet = workbook.active
            
            i = 1
            for product_link_mix in products_url_txt.readlines()[self.start_index:self.end_index]:
                time.sleep(2)
                product_category = product_link_mix.split("::")[0]
                product_link = product_link_mix.split("::")[1]
                link = product_link[:-1]
                self.status_publishing("Product " + str(i) + " : " + link)                
                i += 1
                if link[0] == "/": 
                    link = BASE_URL + link
                
                # try:
                page = s.get(link, headers=headers,timeout=30)
                soup = BeautifulSoup(page.content, 'html.parser')

                try:
                    td = soup.select_one("#ctl00_PageContent_pnlContent").select_one("table").select_one("table").select("td")[1]
                    product_name = soup.select_one(".ProductNameTextinTab").getText()
                    # print(str(self.thread_index) + " product name = ", product_name)
                except:
                    product_name = ""

                try:
                    # print(" == 1 == ", soup.select("#ctl00_PageContent_pnlContent table table td"))
                    # print(" == 2 == ", soup.select("#ctl00_PageContent_pnlContent table table td")[1])
                    # print(" == 3 == ", soup.select("#ctl00_PageContent_pnlContent table table td")[1].select("div")[3])
                    product_description = soup.select("#ctl00_PageContent_pnlContent table table td")[1].select("div")[3].getText()
                    # print(str(self.thread_index) + " product description = ", product_description)
                except:
                    product_description = ""

                try:
                    product_sku = soup.find("td", string="SKU:").find_next_sibling("td").getText()
                    # print(str(self.thread_index) + " sku = ", product_sku)
                except:
                    product_sku = ""
                
                try:
                    product_weight = soup.find("td", string="Weight:").find_next_sibling("td").getText()
                    # print(str(self.thread_index) + " weight = ", product_weight)
                except:
                    product_weight = ""
                
                try:
                    product_stock = soup.find("b", string="In Stock:").parent.getText().split(":")[1].strip()
                    # print(str(self.thread_index) + " stock = ", product_stock)
                except:
                    product_stock = ""

                try:
                    product_price = soup.select_one(".variantprice").getText().split(":")[1].strip()
                    # print(str(self.thread_index) + " price = ", product_price)
                except:
                    product_price = ""

                try:
                    product_img = soup.select_one("#ctl00_PageContent_pnlContent table table td img")["src"]
                    # print(str(self.thread_index) + " img = ", product_img)
                except:
                    product_img = ""


                if stock_scrape == 0:
                    worksheet.cell(column=1, row=i).value=product_sku
                    worksheet.cell(column=2, row=i).value=product_name
                    worksheet.cell(column=3, row=i).value=product_category
                    worksheet.cell(column=4, row=i).value=product_price
                    worksheet.cell(column=5, row=i).value=product_stock
                    worksheet.cell(column=6, row=i).value=product_weight
                    worksheet.cell(column=7, row=i).value=product_description
                    worksheet.cell(column=8, row=i).value=product_link
                    worksheet.cell(column=9, row=i).value=product_img
                else:
                    worksheet.cell(column=1, row=i).value=product_sku
                    worksheet.cell(column=2, row=i).value=product_stock
                    
                # except:
                    # if stock_scrape == 0:
                    #     worksheet.cell(column=8, row=i).value=link
                    # else:
                    #     worksheet.cell(column=3, row=i).value=link

                workbook.save(xlsfile_name)


            self.status_publishing("ended")
            time.sleep(10)
            sys.exit()
            
        
    def status_publishing(self,text) :
        global scrape_status

        scrape_status = text
        self.status = text
        print(text)
