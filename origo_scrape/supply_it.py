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


class Supply_it_Thread(Thread):
 
    def __init__(self, scrape_type):
        Thread.__init__(self)
        self.scrape_type = scrape_type
        self.log = logging.getLogger("a")  # root logger
        self.status = ""


    def login(self, mail, driver) :   
        self.status_publishing("loging in") 
        my_logging(self.log, "login ...")
        driver.get('https://www.supply-it.ie/')
        mail_address = mail[0]
        mail_pass = mail[1]
        time.sleep(5)

    # Click Sign In Link
        while True:
            try:
                sign_in = driver.find_element_by_xpath("//div[@class='panel header']//li[@class='authorization-link']/a")
                sign_in.click()
                self.status_publishing("Sign In Button is clicked.")
                break
            except TimeoutException:
                self.status_publishing("Sign In Button has not found")
                time.sleep(1)

    # Email
        while True:
            try:
                email_field = driver.find_element_by_xpath("//div[@class='panel header']//input[@name='login[username]']")
                email_field.send_keys(mail_address)
                self.status_publishing("Email address is inserted")
                break
            except TimeoutException:
                self.status_publishing("Email field has not found")
                time.sleep(1)

    # Password
        while True:
            try:
                password_field = driver.find_element_by_xpath("//div[@class='panel header']//input[@name='login[password]']")
                password_field.send_keys(mail_pass)
                self.status_publishing("Password is inserted")
                break
            except TimeoutException:
                self.status_publishing("Password field has not found")
                time.sleep(1)
                
    # Sign In Button
        while True:
            try:
                sign_in = driver.find_element_by_xpath("//div[@class='panel header']//button[@type='submit' and ./span='Sign In']")
                sign_in.click()
                self.status_publishing("Sign In Button is clicked")
                break
            except TimeoutException:
                self.status_publishing("Sign In Button has not found")
                time.sleep(1)
        
         
    def run(self):
        now = datetime.now()
        mail_address = os.environ.get('SUPPLY_IT_MAIL_ADDRESS')
        mail_password = os.environ.get('SUPPLY_IT_MAIL_PASSWORD')
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
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        path = join(dirname(__file__), 'webdriver', 'chromedriver.exe') # Windows
        print("platform.system() = " + platform.system())
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
        categories_dict = {}
        product_count = 0
        fields = ['id', 'sku', 'category', 'title', 'stock', 'list price', 'nett price', 'description', 'URL', 'image']
        if stock_scrape == 1: fields = ['id', 'stock']

        # generate .xlsx file name
        timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
        xlsfile_name = 'products-' + timestamp + '.xlsx'
        if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '.xlsx'
        xlsfile_name = join(root_path, "xls", "supply_it", xlsfile_name)

        workbook = xlsxwriter.Workbook(xlsfile_name)
        worksheet = workbook.add_worksheet()

        # Get Category Links
        category_link_list = []
        while True:
            try:
                category_links = driver.find_elements_by_xpath("//li[@class='ui-menu-item level2 ']/a")
                self.status_publishing("Category links had got.")
                break
            except TimeoutException:
                self.status_publishing("Category links have not found")
                time.sleep(1)

        for link in category_links:
            category_link_list.append(link.get_attribute("href"))

        print(category_link_list)

        for link in category_link_list:
            self.status_publishing(link)
            driver.get(link + "?product_list_limit=all")
            # time.sleep(1)
            
            # Get Category
            while True:
                try:
                    category_parts = driver.find_elements_by_xpath("//li[contains(@class, 'item category')]")
                    # self.status_publishing("Category had got.")
                    break
                except TimeoutException:
                    self.status_publishing("Category has not found")
                    # time.sleep(1)
            category = " > ".join([p.text for p in category_parts])
            print("category = " + category)

            # Get Products
            # driver.execute_cdp_cmd('Emulation.setScriptExecutionDisabled', {'value': True})

            while True:
                try:
                    products = driver.find_elements_by_xpath("//div[@class='products wrapper grid columns6  products-grid']//li")
                    # self.status_publishing("Products list had got.")
                    break
                except TimeoutException:
                    self.status_publishing("Products list has not found")
                    # time.sleep(1)

            # Get Product details
            if stock_scrape == 0:
                
            # Full Scrape
                product_link_list = {}
                
                # Get product_id and product_details file name
                for product in products:
                    product_part_1 = product.find_element_by_xpath(".//div[@class='price-box price-final_price']")
                    product_id = product_part_1.get_attribute("data-product-id")

                    if product_id in categories_dict:
                        categories_dict[product_id] += " ; " + category
                        continue
                    else:
                        categories_dict[product_id] = category
                    product_link_elem = product.find_element_by_xpath(".//div[@class='product photo product-item-photo']/a")
                    product_link_list[product_id] = product_link_elem.get_attribute("href")

                # # Get product details
                # print("#" * 50)
                # print(product_link_list)
                # print("#" * 50)

                for product_id in product_link_list:
                    self.status_publishing(product_link_list[product_id])
                    driver.get(product_link_list[product_id])
                    # time.sleep(1)                   
                    product_img = ""
                    while True:
                        try:
                            product_img = driver.find_element_by_xpath("(//div[contains(@data-gallery-role,'gallery')]//img)[1]").get_attribute("src")
                            break
                        except:
                            pass
                        
                    product_title = driver.find_element_by_xpath("//h1[@class='page-title']/span").text
                    product_sku = driver.find_element_by_xpath("//div[@itemprop='sku']").text
                    product_stock = "Out"

                    try:
                        product_stock_avail = driver.find_element_by_xpath("//div[@title='Availability' and @class='stock available']")
                        product_stock = "In"
                    except:
                        pass

                    product_price_list = driver.find_element_by_xpath("//div[@class='product-info-price']//span[@class='price-container price-final_price tax weee rewards_earn']//span[@class='price']").text
                    product_price_nett = ""

                    try:
                        product_price_nett_elem = driver.find_element_by_xpath("//span[@class='price-container price-tier_price tax weee rewards_earn']//span[@class='price']")
                        product_price_nett = product_price_nett_elem.text
                    except:
                        pass
                    
                    product_description = ""
                    try:
                        product_description = driver.find_element_by_xpath("//div[@itemprop='description']").text
                    except:
                        pass

                    

                    try:
                        if product_id in products_dict: 
                            print("duplicate")
                            products_dict[product_id][2] += " ; " + categories_dict[product_id]
                        else:
                            products_dict[product_id] = [str(product_id), product_sku, categories_dict[product_id], product_title, product_stock, product_price_list, product_price_nett, product_description, product_link_list[product_id], product_img]
                    except:
                        pass

                    product_count += 1

            else:

            # Stock Scrape
                for product in products:
                    product_part_1 = product.find_element_by_xpath(".//div[@class='price-box price-final_price']")
                    product_id = product_part_1.get_attribute("data-product-id")
                    
                    product_stock = "In"
                    try:
                        product_stock_unavail = driver.find_element_by_xpath("//div[@class='stock unavailable']")
                        product_stock = "Out"
                    except:
                        pass

                    if not product_id in products_dict: 
                        products_dict[product_id] = [str(product_id), product_stock]
                    product_count += 1
        
        i = -1                                              
        for val in fields:
            i += 1
            worksheet.write(0, i, val)

        i = 0
        for row in products_dict:
            i += 1
            j = -1
            for val in products_dict[row]:
                j += 1
                worksheet.write(i, j, val)
        workbook.close()
        
        print("#" * 50)
        print("count = " + str(product_count))

        self.status_publishing("scraping is ended")
        
        
    def status_publishing(self,text) :
        global scrape_status

        scrape_status = text
        self.status = text
        print(text)
        my_logging(self.log, text)
