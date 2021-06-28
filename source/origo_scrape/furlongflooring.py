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


cur_path = dirname(__file__)
root_path = cur_path[:cur_path.rfind(os.path.sep)]
# root_path = root_path[:root_path.rfind(os.path.sep)]
load_dotenv(join(root_path, '.env'))
log_file_size = 10
formatter = logging.Formatter('%(asctime)s    %(message)s')
scrape_status = ""


def my_logging(log, msg):
    global root_path

    log.propagate = True
    fileh = RotatingFileHandler(join(root_path, "log", "origo.log"), mode='a', maxBytes=log_file_size*1024, backupCount=2, encoding='utf-8', delay=0)
    # ('logs/' + f_name + '.log', 'a')
    fileh.setFormatter(formatter)
    for hdlr in log.handlers[:]:  # remove all old handlers
        log.removeHandler(hdlr)
    log.addHandler(fileh)
    log.critical(msg)
    log.propagate = False


class FF_Thread(Thread):
 
    def __init__(self, scrape_type):
        Thread.__init__(self)
        self.scrape_type = scrape_type
        self.log = logging.getLogger("a")  # root logger
        self.status = ""


    def login(self, mail, driver) :   
        self.status_publishing("loging in") 
        my_logging(self.log, "login ...")
        driver.get('https://online.furlongflooring.com/pgpower/')
        mail_address = mail[0]
        mail_pass = mail[1]
        time.sleep(5)

    # Login Id
        while True:
            try:
                login_id_field = driver.find_element_by_xpath("//input[@name='User']")
                login_id_field.send_keys(mail_address)
                self.status_publishing("Login Id is inserted")
                break
            except TimeoutException:
                self.status_publishing("Login Id field has not found")
                time.sleep(1)

    # Password
        while True:
            try:
                password_field = driver.find_element_by_xpath("//input[@name='Password']")
                password_field.send_keys(mail_pass)
                self.status_publishing("Password is inserted")
                break
            except TimeoutException:
                self.status_publishing("Password field has not found")
                time.sleep(1)
       
    # Sign In Button
        while True:
            try:
                sign_in = driver.find_element_by_xpath("//input[@value='Sign In']")
                sign_in.click()
                self.status_publishing("Sign In Button is clicked")
                break
            except TimeoutException:
                self.status_publishing("Sign In Button has not found")
                time.sleep(1)

    # 'View Stock by Class or Range' Button
        while True:
            try:
                view_btn = driver.find_element_by_xpath("//input[@value='View Stock by Class or Range']         ")
                view_btn.click()
                self.status_publishing("'View Stock by Class or Range' Button is clicked")
                break
            except TimeoutException:
                self.status_publishing("'View Stock by Class or Range' Button has not found")
                time.sleep(1)
        
         
    def run(self):
        now = datetime.now()
        mail_address = os.environ.get('FF_LOGIN_ID')
        mail_password = os.environ.get('FF_PASSWORD')
        mail = [mail_address, mail_password]
        print(mail_address + " :: " + mail_password)

        ua = UserAgent()
        userAgent = ua.random
        userAgent = userAgent.split(" ")
        # userAgent[0] = "Mozilla/5.0"
        userAgent = " ".join(userAgent)
        print("userAgent = " + userAgent)
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('user-agent={0}'.format(userAgent))
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("window-size=1280,800")
        chrome_options.add_argument('--log-level=0')
        path = join(dirname(__file__), 'webdriver', 'chromedriver.exe') # Windows
        if platform.system() == "Linux":
            path = join(dirname(__file__), 'webdriver', 'chromedriver') # Linux

        driver = webdriver.Chrome (executable_path = path, options = chrome_options )
        # driver.maximize_window()
        self.status_publishing("start chrome")
        my_logging(self.log, "start chrome")
        #Remove navigator.webdriver Flag using JavaScript
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        # driver.set_window_size(1200,900)
        try:
            my_logging(self.log, "try")
            self.login(mail, driver)
            time.sleep(5)
            if self.scrape_type == "stock":
                self.loop_main_category(driver, 1)
            else:
                self.loop_main_category(driver)
            print("#" * 50)
            print("time = " + str(datetime.now() - now))
        except Exception as e:
            # driver.save_screenshot(datetime.now().strftime("screenshot_%Y%m%d_%H%M%S_%f.png"))
            self.status_publishing(e)
        finally:
            pass


    def fail_with_error(self, message):
        def decorator(fx):
            def inner(*args, **kwargs):
                try:
                    return fx(*args, **kwargs)
                except Exception as e:
                    self.status_publishing(message)
                    raise e
            return inner
        return decorator


    def loop_main_category(self, driver, stock_scrape=0):
        global root_path

        products_dict = {}
        global_head_list = []
        product_count = 0
        fields = ['id', 'sku', 'category', 'title', 'stock', 'list price', 'nett price', 'description', 'URL', 'image']
        if stock_scrape == 1: fields = ['id', 'stock']

        # generate .xlsx file name
        timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
        xlsfile_name = 'products-' + timestamp + '.xlsx'
        if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '.xlsx'
        xlsfile_name = join(root_path, "xls", "furlongflooring", xlsfile_name)

        workbook = xlsxwriter.Workbook(xlsfile_name)
        worksheet = workbook.add_worksheet()

        # Get Category Links
        category_link_list = []
        # First Column
        while True:
            try:
                category_links = driver.find_elements_by_xpath("//*[@id='pagewrapper']/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/table/tbody/tr[2]/td[1]//ul/li/a")
                self.status_publishing("Category links had got.")
                break
            except TimeoutException:
                self.status_publishing("Category links have not found")
                time.sleep(1)

        for link in category_links:
            if not link.get_attribute("href") in category_link_list:
                category_link_list.append(link.get_attribute("href"))

        # Second Column
        while True:
            try:
                category_links = driver.find_elements_by_xpath("//*[@id='pagewrapper']/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/table/tbody/tr[2]/td[2]//ul/li/a")
                self.status_publishing("Category links had got.")
                break
            except TimeoutException:
                self.status_publishing("Category links have not found")
                time.sleep(1)

        for link in category_links:
            if not link.get_attribute("href") in category_link_list:
                category_link_list.append(link.get_attribute("href"))

        print(category_link_list)

        # Get Sub Category link list **** begin ****
        sub_category_link_list = []
        sub_category_links = driver.find_elements_by_xpath("//*[@id='pagewrapper']/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/table/tbody/tr[2]/td[3]/table/tbody/tr/td/ul/li/a")
        for link in sub_category_links:
            if not link.get_attribute("href") in sub_category_link_list:
                sub_category_link_list.append(link.get_attribute("href"))

        for link in category_link_list:
            self.status_publishing(link)
            driver.get(link)
            time.sleep(1)

            sub_category_links = driver.find_elements_by_xpath("//*[@id='pagewrapper']/table[2]/tbody/tr/td/table/tbody/tr/td[2]/div/table/tbody/tr[2]/td[3]/table/tbody/tr/td/ul/li/a")
            for link in sub_category_links:
                if not link.get_attribute("href") in sub_category_link_list:
                    sub_category_link_list.append(link.get_attribute("href"))
        # Get Sub Category link list **** end ****

        # 
        for link in sub_category_link_list:
            self.status_publishing("link = " + link)
            driver.get(link)
            time.sleep(1)
            
            while True:
                try:
                    head_list_elem = driver.find_elements_by_xpath("html/body/div/table[2]/tbody/tr/td/table/tbody/tr[not(contains(@class, 'stocktd'))]/td")                    
                    break
                except:
                    pass
            
            head_list = []
            for head in head_list_elem:
                head_text = head.text
                if head_text == "Pattern Id": 
                    head_text = "Pattern"
                head_list.append(head_text)
                if not head_text in global_head_list and head_text != " " : global_head_list.append(head_text)

            product_list = driver.find_elements_by_xpath("html/body/div/table[2]/tbody/tr/td/table/tbody/tr[contains(@class, 'stocktd')]")
            for product in product_list:
                product_detail = {}
                for field, item in zip(head_list, product.find_elements_by_xpath("./td")):
                    if field == " ":
                        continue
                    elif field == "Stock":
                        while True:
                            product_stock = item.find_element_by_xpath(".//td").text
                            if product_stock != "Loading..." : break
                        if product_stock.find("(") > -1:
                            product_stock = product_stock[:product_stock.find("(")].strip()
                        product_detail[field] = product_stock
                    else:
                        product_detail[field] = item.text
                
                # print(product_detail)
                
                if product_detail["Item"] in products_dict: 
                    print("duplicate")
                    products_dict[product_detail["Item"]]["Range"] += " ; " + product_detail["Range"]
                else:
                    products_dict[product_detail["Item"]] = product_detail

                product_count += 1

        i = -1  
        field_to_num_dict = {}                                            
        for head in global_head_list:            
            i += 1
            field_to_num_dict[head] = i
            if head == "Item":
                worksheet.write(0, i, "SKU")
            else:
                worksheet.write(0, i, head)

        i = 0
        for row in products_dict:
            i += 1
            j = -1
            for field in products_dict[row]:
                worksheet.write(i, field_to_num_dict[field], products_dict[row][field])
        workbook.close()

        print("#" * 50)
        print("count = " + str(product_count))

        self.status_publishing("scraping is ended")
        
        
    def status_publishing(self,text) :
        global scrape_status

        scrape_status = text
        self.status = text
        print(text)
