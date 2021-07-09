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
    fileh = RotatingFileHandler(join(root_path, "log", "Origo.log"), mode='a', maxBytes=log_file_size*1024, backupCount=2, encoding='utf-8', delay=0)
    # ('logs/' + f_name + '.log', 'a')
    fileh.setFormatter(formatter)
    for hdlr in log.handlers[:]:  # remove all old handlers
        log.removeHandler(hdlr)
    log.addHandler(fileh)
    log.critical(msg)
    log.propagate = False


class Origo_Category_Thread(Thread):
 
    def __init__(self, stock_scrape):
        Thread.__init__(self)
        self.stock_scrape = stock_scrape
        self.log = logging.getLogger("a")  # root logger
        self.status = ""
        
         
    def run(self):
        now = datetime.now()
        mail_address = os.environ.get('ORIGO_MAIL_ADDRESS')
        mail_password = os.environ.get('ORIGO_MAIL_PASSWORD')

        try:
            self.main_loop(mail_address, mail_password, self.stock_scrape)
        except Exception as e:
            # driver.save_screenshot(datetime.now().strftime("screenshot_%Y%m%d_%H%M%S_%f.png"))
            self.status_publishing(e)
        finally:
            pass


    def main_loop(self, user_email, user_password, stock_scrape=0):
        print("main_loop()")
        BASE_URL = "https://origo-online.origo.ie"        
        category_link_list = []

        with requests.Session() as s:
            proxies = {
                "http": "http://Administrator:aaaA111!@16.162.119.238:443",
                "https": "http://Administrator:aaaA111!@16.162.119.238:443",
            }

            p = s.get("https://origo-online.origo.ie")

            print(p)
            # Get SESSION_ID
            cookie = p.headers["Set-Cookie"]
            self.status_publishing("headers = " + p.headers)            
            self.status_publishing("cookie = " + cookie)            

            soup = BeautifulSoup(p.content, 'html.parser')

            lang_id = cookie[1][cookie[1].find("LanguageId"):]
            lang_id = lang_id[lang_id.find("=") + 1:]
            lang_id = lang_id[:lang_id.find(";")]
            self.status_publishing("lang_id = " + lang_id)            
            
            session_id = cookie[2][cookie[2].find("ASP.NET_SessionId"):]
            session_id = session_id[session_id.find("=") + 1:]
            session_id = session_id[:session_id.find(";")]
            self.status_publishing("session_id = " + session_id)

            token = cookie[3][cookie[3].find("__RequestVerificationToken"):]
            token = token[token.find("=") + 1:]
            token = token[:token.find(";")]
            self.status_publishing("token = " + token)

            token_2 = soup.find("form", attr={"action": ""}).find("input", attr={"name": "__RequestVerificationToken"})["value"]
            self.status_publishing("token_2 = " + token_2)

            # Set HEADER
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'cookie': 'LanguageId=' + lang_id + '; ASP.NET_SessionId=' + session_id + '; __RequestVerificationToken=' + token + '; cb-enabled=enabled; \
                    _ga=GA1.2.1368687610.1625816043; _gid=GA1.2.1963759931.1625816043; _gat_gtag_UA_171557395_1=1',
            }

            p = s.post("https://origo-online.origo.ie", data={
                "__RequestVerificationToken": token_2,
                "UserName": user_email,
                "Password": user_password,
                "RememberMe": "false",
            }, headers=headers)

            # Get SESSION_ID
            cookie = p.headers["Set-Cookie"]
            
            xauth_ss_s = cookie[0][cookie[0].find(".ASPXAUTH_SS_s"):]
            xauth_ss_s = xauth_ss_s[xauth_ss_s.find("=") + 1:]
            xauth_ss_s = xauth_ss_s[:xauth_ss_s.find(";")]

            xauth_ss = cookie[1][cookie[1].find(".ASPXAUTH_SS"):]
            xauth_ss = xauth_ss[xauth_ss.find("=") + 1:]
            xauth_ss = xauth_ss[:xauth_ss.find(";")]

            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'cookie': 'LanguageId=' + lang_id + '; ASP.NET_SessionId=' + session_id + '; __RequestVerificationToken=' + token + '; \
                    cb-enabled=enabled; _ga=GA1.2.1368687610.1625816043; _gid=GA1.2.1963759931.1625816043; _gat_gtag_UA_171557395_1=1; \
                    .ASPXAUTH_SS_s=' + xauth_ss_s + '; .ASPXAUTH_SS=' + xauth_ss
            }
            self.status_publishing("headers = " + headers)

    # START --- GET PRODUCT LINK --- 

    #         products_url_txt = open("origo_products_url.txt","w")
    #         base_page = s.get('https://origo-online.origo.ie/default.aspx')
    #         soup = BeautifulSoup(base_page.content, 'html.parser')
    #         for main_category in soup.select("#Categories ul li a"):
    #             category_link_list.append({"name": main_category.getText(), "href": main_category['href']})
    #         print(category_link_list)
            
    #         # Get Products Links
    #         for category_link in category_link_list:
    #             link = category_link["href"]
    #             if link[0] == "/": 
    #                 link = BASE_URL + link
    #             page = s.get(link, headers=headers)
    #             soup = BeautifulSoup(page.content, 'html.parser')
                
    #             sub_categories = soup.select(".subentityResult")
    #             for sub_category in sub_categories:
    #                 href = sub_category.select("a")[1]["href"]
    #                 name = sub_category.select("a")[1].select_one("span").getText()
    #                 category_link_list.append({"name": category_link["name"] + " / " + name, "href": href})

    #             page_num = 1
    #             while True:
    #                 self.status_publishing("Category Link : " + category_link["name"] + ", Page number : " + str(page_num))
    #                 is_last = False
    #                 for product in soup.select(".productResult"):
    #                     product_link = product.select('div h2 a')[0]["href"]
    #                     print(product_link)
    #                     products_url_txt.write(category_link["name"] + "::" + product_link + "\n")

    #                 next_btn = soup.find_all("li", attrs={'class':'pagingPreviousNext'}, string="Next »")
    #                 print("next_btn = ", next_btn)
    #                 if len(next_btn) == 0 or next_btn[0]["class"][-1] == "pagingDisabled": break
                
    #                 page_num += 1
    #                 page = s.get(link + "?pagenum=" + str(page_num), headers=headers)
    #                 soup = BeautifulSoup(page.content, 'html.parser')

    #         products_url_txt.close()

    # # END --- GET PRODUCT LINK ---   
    #         self.status_publishing("ended")
    #         time.sleep(10)
    #         sys.exit()
            
        
    def status_publishing(self,text) :
        global scrape_status

        scrape_status = text
        self.status = text
        print(text)
