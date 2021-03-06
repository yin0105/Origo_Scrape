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


class RDS_Thread(Thread):
 
    def __init__(self, thread_index, start_index, end_index, stock_scrape):
        Thread.__init__(self)
        self.stock_scrape = stock_scrape
        self.start_index = start_index + 519
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

        fields = ['SKU', 'Name', 'Description', 'Trade Price', 'SRP Price', 'Price', 'Stock', 'URL', 'Image', 'Category', 'Commodity Code', 'Barcode', 'Shipping Dimensions', 'Shipping Weight', 'Country of Origin', 'Colour', 'Length']
        if stock_scrape == 1: fields = ['SKU', 'Name', 'Stock', 'URL']

        # generate .xlsx file name
        timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
        xlsfile_name = str(self.thread_index) + '-temp.xlsx'
        # if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '-' + str(self.thread_index) + '-temp.xlsx'
        xlsfile_name = join(root_path, "xls", "reydonsports", xlsfile_name)
        print(xlsfile_name)        

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

            products_url_txt = open("reydonsports_products_url.txt","r")
            
            # workbook = xlsxwriter.Workbook(xlsfile_name)
            # worksheet = workbook.add_worksheet()
            # i = -1  
            # for head in fields:
            #     i += 1            
            #     worksheet.write(0, i, head)
            # workbook.close()

            workbook = openpyxl.load_workbook(xlsfile_name)
            worksheet = workbook.active
            
            i = 520

            for product_link in products_url_txt.readlines()[self.start_index:self.end_index]:
            # for product_link in products_link_list:
                link = product_link[:-1]
                self.status_publishing("Product " + str(i) + " : " + link)                
                i += 1
                if link[0] == "/": 
                    link = BASE_URL + link
                
                try:
                    page = s.get(link, headers=headers)
                    soup = BeautifulSoup(page.content, 'html.parser')

                    form = str(soup.find('form', attrs={'class':'js_add_cart_variants'})['data-attribute_value_ids'])
                    form = form[form.find("default_code"):]
                    form = form[form.find(":"):]
                    form = form[form.find("'") + 1 :]
                    product_sku = form[:form.find("'")]
                    product_name = soup.find('div', attrs={'class':'c_product_name'}).get_text()
                    product_stock = soup.find('div', attrs={'class':'availability_messages css_rey_is_not_available'}).div.get_text().strip()

                    if stock_scrape == 0:
                        
                        product_desc = soup.find('div', attrs={'class':'o_not_editable prod_des'}).get_text()

                        product_price_trade = soup.find('h6', attrs={'id':'rey_trade_price'}).get_text().split(":")
                        if len(product_price_trade) > 1: 
                            product_price_trade = product_price_trade[1].strip()
                        else:
                            product_price_trade = product_price_trade[0].strip()

                        product_price_srp = soup.find('h6', attrs={'id':'rey_srp_price'}).get_text().split(":")
                        if len(product_price_srp) > 1: 
                            product_price_srp = product_price_srp[1].strip()
                        else:
                            product_price_srp = product_price_srp[0].strip()

                        product_price = soup.find('h4', attrs={'class':'oe_price_h4 css_editable_mode_hidden'}).b.get_text().replace(u'\xa0', u' ')

                        
                        product_img = soup.find('img', attrs={'class':'img img-responsive product_detail_img js_variant_img'})['src']
                        product_category = soup.find('p', attrs={'class':'category_label'}).a.get_text()
                        
                        
                        
                        try:
                            product_intrastat = soup.find('td', attrs={'id':'product_intrastat'}).get_text().strip()
                        except:
                            product_intrastat = ""

                        try:
                            product_barcode = soup.find('td', attrs={'id':'product_barcode'}).get_text().strip()
                        except:
                            product_barcode = ""

                        try:                
                            product_dimensions = soup.find('td', attrs={'id':'product_dimensions'}).get_text().strip()
                        except:
                            product_dimensions = ""

                        try:
                            product_weight = soup.find('td', attrs={'id':'product_weight'}).get_text().strip()
                        except:
                            product_weight = ""

                        try:
                            product_origin = soup.find('td', attrs={'id':'product_origin'}).get_text().strip()
                        except:
                            product_origin = ""
                        
                        try:
                            product_color = soup.find("td", string="Colour").find_next_sibling("td").get_text().strip()
                        except:
                            product_color = ""
                        
                        try:
                            product_length = soup.find("td", string="Length").find_next_sibling("td").get_text().strip()
                        except:
                            product_length = ""

                    if stock_scrape == 0:
                        worksheet.cell(column=1, row=i).value=product_sku
                        worksheet.cell(column=2, row=i).value=product_name
                        worksheet.cell(column=3, row=i).value=product_desc
                        worksheet.cell(column=4, row=i).value=product_price_trade
                        worksheet.cell(column=5, row=i).value=product_price_srp
                        worksheet.cell(column=6, row=i).value=product_price
                        worksheet.cell(column=7, row=i).value=product_stock
                        worksheet.cell(column=8, row=i).value=link
                        worksheet.cell(column=9, row=i).value=product_img
                        worksheet.cell(column=10, row=i).value=product_category
                        worksheet.cell(column=11, row=i).value=product_intrastat
                        worksheet.cell(column=12, row=i).value=product_barcode
                        worksheet.cell(column=13, row=i).value=product_dimensions
                        worksheet.cell(column=14, row=i).value=product_weight
                        worksheet.cell(column=15, row=i).value=product_origin
                        worksheet.cell(column=16, row=i).value=product_color
                        worksheet.cell(column=17, row=i).value=product_length
                        # worksheet.write(i, 0, product_sku)
                        # worksheet.write(i, 1, product_name)
                        # worksheet.write(i, 2, product_desc)
                        # worksheet.write(i, 3, product_price_trade)
                        # worksheet.write(i, 4, product_price_srp)
                        # worksheet.write(i, 5, product_price)
                        # worksheet.write(i, 6, product_stock)
                        # worksheet.write(i, 7, product_link[:-1])
                        # worksheet.write(i, 8, product_img)
                        # worksheet.write(i, 9, product_category)
                        # worksheet.write(i, 10, product_intrastat)
                        # worksheet.write(i, 11, product_barcode)
                        # worksheet.write(i, 12, product_dimensions)
                        # worksheet.write(i, 13, product_weight)
                        # worksheet.write(i, 14, product_origin)
                        # worksheet.write(i, 15, product_color)
                        # worksheet.write(i, 16, product_length)
                    else:
                        worksheet.cell(column=0, row=i).value=product_sku
                        worksheet.cell(column=1, row=i).value=product_name
                        worksheet.cell(column=2, row=i).value=product_stock
                        worksheet.cell(column=3, row=i).value=link
                        # worksheet.write(i, 0, product_sku)
                        # worksheet.write(i, 1, product_name)
                        # worksheet.write(i, 2, product_stock)
                    
                    # workbook.close()
                except:
                    if stock_scrape == 0:
                        worksheet.cell(column=8, row=i).value=link
                    else:
                        worksheet.cell(column=3, row=i).value=link

                workbook.save(xlsfile_name)


            self.status_publishing("ended")
            time.sleep(10)
            sys.exit()
            
        
    def status_publishing(self,text) :
        global scrape_status

        scrape_status = text
        self.status = text
        print(text)
