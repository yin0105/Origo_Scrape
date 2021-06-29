# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.template import loader
from django.forms.utils import ErrorList
from django.http import HttpResponse
from .origo import Origo_Thread
from .supply_it import Supply_it_Thread
from .furlongflooring import FF_Thread
from .reydonsports import RDS_Thread
from os.path import join, dirname
# from .origo import scrape_status as origo_scrape_status
import glob, os, zipfile, openpyxl, xlsxwriter
from os import path
from django.contrib.auth.decorators import login_required

from bs4 import BeautifulSoup
import requests
from datetime import datetime


# from filewrap import Filewrapper


# dotenv_path = join(dirname(__file__), '.env')
# load_dotenv(dotenv_path)
cur_path = dirname(__file__)
root_path = cur_path[:cur_path.rfind(os.path.sep)]
# root_path = root_path[:root_path.rfind(os.path.sep)]
cur_site = ""
t_origo = None
t_supply_it = None
t_ff = None
t_rds = None
# sites = [{"url": "https://origo-online.origo.ie", "short": "origo"}, {"url": "https://www.supply-it.ie/", "short": "supply_it"}, {"url": "https://online.furlongflooring.com/", "short": "furlongflooring"}]
sites = [{"url": "https://www.reydonsports.com/", "short": "reydonsports"}]
# sites = [{"url": "https://www.supply-it.ie/", "short": "supply_it"}]
scrape_status = None


@login_required
def index(request):
    global sites
    # return render(request, "index.html")
    context = {}
    context['sites'] = sites
    html_template = loader.get_template( 'main/index.html' )
    return HttpResponse(html_template.render(context, request))


@login_required
def start_scrape(request):
    global t_origo, t_supply_it, t_ff, t_rds, cur_site

    print("start_scrape")
    cur_site = request.GET["site"]
    scrape_type = request.GET["scrape_type"]
    if cur_site == "origo":
        if t_origo == None:
            t_origo = Origo_Thread(scrape_type)
            t_origo.start()
    elif cur_site == "supply_it":
        if t_supply_it == None:
            t_supply_it = Supply_it_Thread(scrape_type)
            t_supply_it.start()
    elif cur_site == "furlongflooring":
        if t_ff == None:
            t_ff = FF_Thread(scrape_type)
            t_ff.start()
    elif cur_site == "reydonsports":
        if t_rds == None:
            t_rds = "Started"
            reydonsports_scrape()
            # t_rds = RDS_Thread(scrape_type)
            # t_rds.start()

    return HttpResponse(root_path)

@login_required
def get_scraping_status(request):
    global t_origo, t_supply_it, t_ff, t_rds
    res = ""
    cur_site = request.GET["site"]

    if cur_site == "origo" :
        res = t_origo.status
    elif cur_site == "supply_it" :
        res = t_supply_it.status
    elif cur_site == "furlongflooring" :
        res = t_ff.status
    elif cur_site == "reydonsports" :
        res = scrape_status
        # res = origo_scrape_status
    # if cur_site == "supply_it" :
    #     res = supply_it_scrape_status
    # if cur_site == "furlongflooring" :
    #     res = furlongflooring_scrape_status
        
    
    return HttpResponse(res)
    
@login_required
def get_xls_list(request):
    global root_path
    
    res = ""
    for site in sites:
        products_arr = []
        stock_arr = []
        
        for file in glob.glob(join(root_path, "xls", site["short"], "products-2*.xlsx")):
            products_arr.append(file[file.rfind(os.path.sep) + 10 : -5])
        for file in glob.glob(join(root_path, "xls", site["short"], "stock-2*.xlsx")):
            stock_arr.append(file[file.rfind(os.path.sep) + 7 : -5])
        products_arr.sort(reverse=True)
        stock_arr.sort(reverse=True)
        if res != "": res += ", "
        res += '"' + site["short"] + '": {"full": "' + '_'.join(products_arr) + '", "stock": "' + '_'.join(stock_arr) + '"}'
    res = '{' + res + '}'
    
    return HttpResponse(res)

@login_required
def download(request):
# Create file_name & file_path
    site = request.GET["site"]
    stock = request.GET["stock"]
    diff = request.GET["diff"]
    recent = request.GET["recent"]
    compare = request.GET["compare"]
    
    file_prefix = "products-"
    if stock == "1" : file_prefix = "stock-"
    
    file_name = file_prefix
    if diff == "1" : file_name += "diff-"
    file_name += recent
    if diff == "1" : file_name += "_" + compare
    zipfile_name = site + "-" + file_name + ".zip"
    file_name += ".xlsx"
    print("file_name = " + file_name)

    file_path = []
    if diff =="1":
        file_path.append(os.path.join(root_path, "xls", site, file_prefix + "add-" + recent + "_" + compare + ".xlsx"))
        file_path.append(os.path.join(root_path, "xls", site, file_prefix + "remove-" + recent + "_" + compare + ".xlsx"))
        zipfile_name = site + "-" + file_prefix + "compare-" + recent + "_" + compare + ".zip"
    else:
        file_path.append(os.path.join(root_path, "xls", site, file_name))

    response = HttpResponse(content_type='application/zip')
    zf = zipfile.ZipFile(response, 'w')

    for file in file_path:
        # Generate if there is no different .xlsx file
        print("file = " + file)
        if diff == "1" and not path.exists(file) :
            compare_xlsx(site, stock, recent, compare)
        with open(file, 'rb') as fh:
            zf.writestr(file[file.rfind(os.path.sep) + 1:], fh.read())

        # return as zipfile
    response['Content-Disposition'] = f'attachment; filename={zipfile_name}'
    return response

@login_required
def compare_xlsx(site, stock, recent, compare) :
    print("*************  compare_xlsx")
    global root_path

    # fields = ['id', 'category', 'title', 'stock', 'list price', 'nett price', 'description', 'URL', 'image']
    fields = []
    file_prefix = "products-"
    if stock == "1": 
        # fields = ['id', 'stock']
        file_prefix = "stock-"
 
    add_file_name = file_prefix + "add-" + recent + "_" + compare + ".xlsx"
    remove_file_name = file_prefix + "remove-" + recent + "_" + compare + ".xlsx"
    older_products = {}
    newer_products = {}

    wb_obj = openpyxl.load_workbook(join(root_path, "xls", site, file_prefix + compare + ".xlsx"))
    sheet = wb_obj.active

    older_products = {}

    for i, row in enumerate(sheet.iter_rows(values_only=True)):
        if i == 0:
            fields = row
        else:
            try:
                if row[0] in older_products: continue
            except:
                pass
            older_products[row[0]] = row
    print(str(len(older_products)))

    wb_obj = openpyxl.load_workbook(join(root_path, "xls", site, file_prefix + recent + ".xlsx"))
    sheet = wb_obj.active

    newer_products = {}

    for i, row in enumerate(sheet.iter_rows(values_only=True)):
        if i > 0:
            try:
                if row[0] in newer_products: continue
            except:
                pass
            newer_products[row[0]] = row
    print(str(len(newer_products)))

    older_products_2 = older_products.copy()

    for row in older_products_2:
        try:
            if row in newer_products:
                del older_products[row]
                del newer_products[row]
        except:
            pass

    workbook = xlsxwriter.Workbook(join(root_path, "xls", site, add_file_name))
    worksheet = workbook.add_worksheet("Add")

    i = -1                                              
    for val in fields:
        i += 1
        worksheet.write(0, i, val)
    
    i = 0
    for row in newer_products:
        i += 1
        j = -1
        for val in newer_products[row]:
            j += 1
            worksheet.write(i, j, val)
    workbook.close()

    workbook = xlsxwriter.Workbook(join(root_path, "xls", site, remove_file_name))
    worksheet = workbook.add_worksheet("Remove")

    i = -1                                              
    for val in fields:
        i += 1
        worksheet.write(0, i, val)
    
    i = 0
    for row in older_products:
        i += 1
        j = -1
        for val in older_products[row]:
            j += 1
            worksheet.write(i, j, val)
    workbook.close()
    
    print("##############  add #############")
    print(str(len(newer_products)))
    print("##############  remove #############")
    print(str(len(older_products)))


def status_publishing(text) :
    global scrape_status

    scrape_status = text
    print(text)


def reydonsports_scrape(stock_scrape=0):
    BASE_URL = "https://www.reydonsports.com"        
    category_link_list = []
    products_link_list = []
    products_dict = {}
    user_email = os.environ.get('RDS_LOGIN_ID')
    user_password = os.environ.get('RDS_PASSWORD')

    fields = ['SKU', 'Name', 'Description', 'Trade Price', 'SRP Price', 'Price', 'Stock', 'URL', 'Image', 'Category', 'Commodity Code', 'Barcode', 'Shipping Dimensions', 'Shipping Weight', 'Country of Origin', 'Colour', 'Length']
    if stock_scrape == 1: fields = ['sku', 'stock']

    # generate .xlsx file name
    timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
    xlsfile_name = 'products-' + timestamp + '.xlsx'
    if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '.xlsx'
    xlsfile_name = join(root_path, "xls", "reydonsports", xlsfile_name)
    print(xlsfile_name)

    workbook = xlsxwriter.Workbook(xlsfile_name)
    worksheet = workbook.add_worksheet()

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
            page = s.get(link)
            soup = BeautifulSoup(page.content, 'html.parser')
            page_num = 1
            while True:
                status_publishing("Category Link : " + category_link + ", Page number : " + str(page_num))
                products = soup.find_all('div', attrs={'class':'oe_product oe_shop_left oe_product_cart'})
                for product in products:
                    a = product.find('a', attrs={'itemprop': 'url'})
                    print(a['href'])
                    products_link_list.append(a['href'])
                    products_url_txt.write(a['href'] + "\n")

                next_btn = soup.find("a", string="Next")
                if next_btn and next_btn['href'] != "":
                    page_num += 1
                    if link.find("?"):
                        link_1 = link[:link.find("?")]
                        # link_2 = link[link.find("?"):]
                        page = s.get(link_1 + "/page/" + str(page_num))
                    else:
                        page = s.get(link + "/page/" + str(page_num))
                    soup = BeautifulSoup(page.content, 'html.parser')
                else:
                    break

        products_url_txt.close()

        products_url_txt = open("reydonsports_products_url.txt","r")

        
        
        i = -1  
        for head in fields:
            i += 1            
            worksheet.write(0, i, head)
        i = 0
        for product_link in products_url_txt.readlines():
        # for product_link in products_link_list:
            i += 1
            link = product_link[:-1]
            status_publishing("Product " + str(i) + " : " + link)                
            if link[0] == "/": 
                link = BASE_URL + link
            page = s.get(link, headers=headers)
            soup = BeautifulSoup(page.content, 'html.parser')
            print(soup.find('div', attrs={'class':'c_product_name'}))
            product_name = soup.find('div', attrs={'class':'c_product_name'}).get_text()
            print(product_name)

            product_desc = soup.find('div', attrs={'class':'o_not_editable prod_des'}).get_text()
            print("product desc :: ", product_desc)

            product_price_trade = soup.find('h6', attrs={'id':'rey_trade_price'}).get_text().split(":")
            if len(product_price_trade) > 1: 
                product_price_trade = product_price_trade[1].strip()
            else:
                product_price_trade = product_price_trade[0].strip()
            print("product trade price :: ", product_price_trade)

            product_price_srp = soup.find('h6', attrs={'id':'rey_srp_price'}).get_text().split(":")
            print("product SRP price :: ", product_price_srp)
            if len(product_price_srp) > 1: 
                product_price_srp = product_price_srp[1].strip()
            else:
                product_price_srp = product_price_srp[0].strip()

            product_price = soup.find('h4', attrs={'class':'oe_price_h4 css_editable_mode_hidden'}).b.get_text().replace(u'\xa0', u' ')

            product_stock = soup.find('div', attrs={'class':'availability_messages css_rey_is_not_available'}).div.get_text().strip()
            product_img = soup.find('img', attrs={'class':'img img-responsive product_detail_img js_variant_img'})['src']
            print("img = ", product_img)

            product_category = soup.find('p', attrs={'class':'category_label'}).a.get_text()
            product_sku = soup.find('p', attrs={'class':'sku_label'}).get_text().strip()
            if product_sku == "":
                product_sku = soup.find('span', attrs={'id':'rey_sku_label'}).get_text().strip()
            print("sku = #", product_sku , "#")
            product_sku = product_sku.split(":")
            print(len(product_sku))
            if len(product_sku) > 1: 
                product_sku = product_sku[1].strip()
            else:
                product_sku = product_sku[0].strip()

            print("SKU = ", product_sku)
            
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

            # if product_name not in products_dict: 
            #     product = {}
            #     product["name"] = product_name
            #     product["url"] = product_link[:-1]
            #     product["desc"] = product_desc
            #     product["price_trade"] = product_price_trade
            #     product["price_srp"] = product_price_srp
            #     product["price"] = product_price
            #     product["stock"] = product_stock
            #     product["img"] = product_img
            #     product["intrastat"] = product_intrastat
            #     product["barcode"] = product_barcode
            #     product["dimensions"] = product_dimensions
            #     product["weight"] = product_weight
            #     product["origin"] = product_origin
            #     product["category"] = product_category
            #     product["sku"] = product_sku
            #     product["color"] = product_color
            #     product["length"] = product_length

            #     print("\n == product == ", product, "\n")

            worksheet.write(i, 0, product_sku)
            worksheet.write(i, 1, product_name)
            worksheet.write(i, 2, product_desc)
            worksheet.write(i, 3, product_price_trade)
            worksheet.write(i, 4, product_price_srp)
            worksheet.write(i, 5, product_price)
            worksheet.write(i, 6, product_stock)
            worksheet.write(i, 7, product_link[:-1])
            worksheet.write(i, 8, product_img)
            worksheet.write(i, 9, product_category)
            worksheet.write(i, 10, product_intrastat)
            worksheet.write(i, 11, product_barcode)
            worksheet.write(i, 12, product_dimensions)
            worksheet.write(i, 13, product_weight)
            worksheet.write(i, 14, product_origin)
            worksheet.write(i, 15, product_color)
            worksheet.write(i, 16, product_length)

        workbook.close()