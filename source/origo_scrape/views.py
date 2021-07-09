# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.template import loader
from django.forms.utils import ErrorList
from django.http import HttpResponse
from .origo import Origo_Thread
from .origo_category import Origo_Category_Thread
from .supply_it import Supply_it_Thread
from .furlongflooring import FF_Thread
from .reydonsports import RDS_Thread
from .reydonsports_category import RDS_Category_Thread
from .totalimports import TotalImports_Thread
from .totalimports_category import TotalImports_Category_Thread
from os.path import join, dirname
# from .origo import scrape_status as origo_scrape_status
import glob, os, zipfile, openpyxl, xlsxwriter
from os import path
from django.contrib.auth.decorators import login_required

from bs4 import BeautifulSoup
import requests, time, math
from datetime import datetime


# from filewrap import Filewrapper


# dotenv_path = join(dirname(__file__), '.env')
# load_dotenv(dotenv_path)
cur_path = dirname(__file__)
root_path = cur_path[:cur_path.rfind(os.path.sep)]
# root_path = root_path[:root_path.rfind(os.path.sep)]
cur_site = ""
# t_origo = None

t_origo = []
t_origo_cat = None

t_supply_it = None
t_ff = None

t_rds = []
t_rds_cat = None

t_totalimports = []
t_totalimports_cat = None
t_totalimports_delay = []


# sites = [{"url": "https://origo-online.origo.ie", "short": "origo"}, {"url": "https://www.supply-it.ie/", "short": "supply_it"}, {"url": "https://online.furlongflooring.com/", "short": "furlongflooring"}]
# sites = [{"url": "https://www.reydonsports.com/", "short": "reydonsports"}]
# sites = [{"url": "https://www.supply-it.ie/", "short": "supply_it"}]
# sites = [{"url": "http://totalimports.ie/", "short": "totalimports"}]
sites = [{"url": "https://origo-online.origo.ie", "short": "origo"}]
# sites = [{"url": "https://online.furlongflooring.com/", "short": "furlongflooring"}]
scrape_status = None
THREAD_COUNT = 5
ALLOW_DELAY = 120


@login_required
def index(request):
    global sites

    context = {}
    context['sites'] = sites
    html_template = loader.get_template( 'main/index.html' )
    return HttpResponse(html_template.render(context, request))


@login_required
def start_scrape(request):
    global t_origo, t_supply_it, t_ff, t_rds, t_totalimports, t_totalimports_cat, t_totalimports_delay, cur_site, stock_scrape

    print("start_scrape")
    cur_site = request.GET["site"]
    scrape_type = request.GET["scrape_type"]
    if cur_site == "origo":
        if len(t_origo) == 0 and t_origo_cat == None:
            stock_scrape = 0
            if scrape_type == "stock": stock_scrape = 1
            origo_category_scrape(stock_scrape)
            # totalimports_scrape(stock_scrape)

        # if t_origo == None or t_origo.status == "scraping is ended":
        #     t_origo = Origo_Thread(scrape_type)
        #     t_origo.start()
    elif cur_site == "supply_it":
        if t_supply_it == None:
            t_supply_it = Supply_it_Thread(scrape_type)
            t_supply_it.start()
    elif cur_site == "furlongflooring":
        if t_ff == None or t_ff.status == "scraping is ended":
            t_ff = FF_Thread(scrape_type)
            t_ff.start()
    elif cur_site == "reydonsports":
        if len(t_rds) == 0 and t_rds_cat == None:
            stock_scrape = 0
            if scrape_type == "stock": stock_scrape = 1
            reydonsports_scrape(stock_scrape)
    elif cur_site == "totalimports":
        if len(t_totalimports) == 0 and t_totalimports_cat == None:
            stock_scrape = 0
            if scrape_type == "stock": stock_scrape = 1
            totalimports_category_scrape(stock_scrape)
            # totalimports_scrape(stock_scrape)

    return HttpResponse(root_path)

@login_required
def get_scraping_status(request):
    global t_origo, t_origo_cat, t_supply_it, t_ff, t_rds, t_rds_cat, t_totalimports, t_totalimports_cat, t_totalimports_delay, stock_scrape, scrape_status
    res = ""
    cur_site = request.GET["site"]

    if cur_site == "origo" :
        # res = t_origo.status

        if len(t_origo) > 0: 
            scrape_status = ""
            for tt in t_origo:
                try:
                    scrape_status += tt.status + "\n"
                except:
                    scrape_status += "\n"
            # scrape_status = "\n".join([tt.status for tt in t_origo if tt != None])
            i = 0
            for t in t_origo:
                i += 1
                try:
                    if t.status != "ended": 
                        break
                except:
                    pass

                if i == len(t_origo):
                    # generate .xlsx file name
                    timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
                    xlsfile_name = 'products-' + timestamp + '.xlsx'
                    if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '.xlsx'
                    xlsfile_name = join(root_path, "xls", "origo", xlsfile_name)

                    workbook = xlsxwriter.Workbook(xlsfile_name)
                    worksheet = workbook.add_worksheet()
                    
                    row_num = 0
                    for j in range(THREAD_COUNT):
                        tmp_wb_obj = openpyxl.load_workbook(join(root_path, "xls", "origo", str(j) + "-temp.xlsx"))
                        sheet = tmp_wb_obj.active
                        
                        for k, row in enumerate(sheet.iter_rows(values_only=True)):
                            if k == 0:
                                if j == 0:
                                    # Write Header
                                    for val, col in zip(row, range(len(row))):
                                        worksheet.write(0, col, val)
                            else:
                                row_num += 1
                                for val, col in zip(row, range(len(row))):
                                    worksheet.write(row_num, col, val)
                        
                        tmp_wb_obj.close()
                    workbook.close()
                    scrape_status = "scraping is ended"
                    break
        elif t_origo_cat != None:
            scrape_status = t_origo_cat.status            
            if scrape_status == "ended":
                t_origo_cat = None
                origo_scrape(stock_scrape)
                # totalimports_scrape()
        
        res = scrape_status 
        if scrape_status == "scraping is ended":
            t_origo.clear()

    elif cur_site == "supply_it" :
        res = t_supply_it.status
    elif cur_site == "furlongflooring" :
        res = t_ff.status
    elif cur_site == "reydonsports" :
        if len(t_rds) > 0: 
            scrape_status = ""
            for tt in t_rds:
                try:
                    scrape_status += tt.status + "\n"
                except:
                    scrape_status += "\n"
            # scrape_status = "\n".join([tt.status for tt in t_rds if tt != None])
            i = 0
            for t in t_rds:
                i += 1
                try:
                    if t.status != "ended": 
                        break
                except:
                    pass

                if i == len(t_rds):
                    # generate .xlsx file name
                    timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
                    xlsfile_name = 'products-' + timestamp + '.xlsx'
                    if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '.xlsx'
                    xlsfile_name = join(root_path, "xls", "reydonsports", xlsfile_name)

                    workbook = xlsxwriter.Workbook(xlsfile_name)
                    worksheet = workbook.add_worksheet()
                    
                    row_num = 0
                    for j in range(THREAD_COUNT):
                        tmp_wb_obj = openpyxl.load_workbook(join(root_path, "xls", "reydonsports", str(j) + "-temp.xlsx"))
                        sheet = tmp_wb_obj.active
                        
                        for k, row in enumerate(sheet.iter_rows(values_only=True)):
                            if k == 0:
                                if j == 0:
                                    # Write Header
                                    for val, col in zip(row, range(len(row))):
                                        worksheet.write(0, col, val)
                            else:
                                row_num += 1
                                for val, col in zip(row, range(len(row))):
                                    worksheet.write(row_num, col, val)
                        
                        tmp_wb_obj.close()
                    workbook.close()
                    scrape_status = "scraping is ended"
                    break
        elif t_rds_cat != None:
            scrape_status = t_rds_cat.status            
            if scrape_status == "ended":
                t_rds_cat = None
                reydonsports_scrape(stock_scrape)
                # totalimports_scrape()
        
        res = scrape_status 
        if scrape_status == "scraping is ended":
            t_rds.clear()

    elif cur_site == "totalimports" :
        if len(t_totalimports) > 0: 
            
            # check if thread works fine
            pre_scrape_status = []
            if scrape_status != None: pre_scrape_status = scrape_status.split("\n")
            scrape_status = ""

            for tt, i in zip(t_totalimports, range(len(t_totalimports))):
                if tt.status != "ended" and len(pre_scrape_status) > i and pre_scrape_status[i] == tt.status:
                    t_totalimports_delay[i] += 1
                    if t_totalimports_delay[i] >= ALLOW_DELAY:
                        totalimports_thread_start(i, stock_scrape)
                else:
                    t_totalimports_delay[i] = 0
                try:
                    scrape_status += tt.status + "\n"
                except:
                    scrape_status += "\n"
            # scrape_status = "\n".join([tt.status for tt in t_totalimports if tt != None])
            i = 0
            for t in t_totalimports:
                i += 1
                try:
                    if t.status != "ended": 
                        break
                except:
                    pass

                if i == len(t_totalimports):
                    # generate .xlsx file name
                    timestamp = datetime.now().strftime("%Y-%m%d-%H%M%S")
                    xlsfile_name = 'products-' + timestamp + '.xlsx'
                    if stock_scrape == 1: xlsfile_name = 'stock-' + timestamp + '.xlsx'
                    xlsfile_name = join(root_path, "xls", "totalimports", xlsfile_name)

                    workbook = xlsxwriter.Workbook(xlsfile_name)
                    worksheet = workbook.add_worksheet()
                    
                    row_num = 0
                    for j in range(THREAD_COUNT):
                        tmp_wb_obj = openpyxl.load_workbook(join(root_path, "xls", "totalimports", str(j) + "-temp.xlsx"))
                        sheet = tmp_wb_obj.active
                        
                        for k, row in enumerate(sheet.iter_rows(values_only=True)):
                            if k == 0:
                                if j == 0:
                                    # Write Header
                                    for val, col in zip(row, range(len(row))):
                                        worksheet.write(0, col, val)
                            else:
                                row_num += 1
                                for val, col in zip(row, range(len(row))):
                                    worksheet.write(row_num, col, val)
                        
                        tmp_wb_obj.close()
                    workbook.close()
                    scrape_status = "scraping is ended"
                    break
        elif t_totalimports_cat != None:
            scrape_status = t_totalimports_cat.status            
            if scrape_status == "ended":
                t_totalimports_cat = None
                # reydonsports_scrape()
                totalimports_scrape(stock_scrape)
        
        res = scrape_status 
        if scrape_status == "scraping is ended":
            t_totalimports.clear()
    
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
        if diff == "1" and not path.exists(file) :
            compare_xlsx(site, stock, recent, compare)
        with open(file, 'rb') as fh:
            zf.writestr(file[file.rfind(os.path.sep) + 1:], fh.read())

        # return as zipfile
    response['Content-Disposition'] = f'attachment; filename={zipfile_name}'
    return response

@login_required
def compare_xlsx(site, stock, recent, compare) :
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
    

def status_publishing(text) :
    global scrape_status

    scrape_status = text


def reydonsports_category_scrape(stock_scrape=0):
    global t_rds_cat, t_rds
    t_rds_cat = RDS_Category_Thread(stock_scrape)
    t_rds_cat.start()


def reydonsports_scrape(stock_scrape=0):
    global t_rds
    products_url_txt = open("reydonsports_products_url.txt","r")
    lines = len(products_url_txt.readlines())
    
    start_index = 0        
    
    for i in range(THREAD_COUNT):
        end_index = start_index + math.ceil(lines / THREAD_COUNT)
        if end_index > lines + 1: end_index = lines + 1
        th = RDS_Thread(i, start_index, end_index, stock_scrape)
        th.start()
        t_rds.append(th)

        start_index = end_index


def totalimports_category_scrape(stock_scrape=0):
    global t_totalimports_cat, t_totalimports
    t_totalimports_cat = TotalImports_Category_Thread(stock_scrape)
    t_totalimports_cat.start()


def totalimports_thread_start(thread_index, stock_scrape=0):
    global t_totalimports, t_totalimports_delay
    products_url_txt = open("totalimports_products_url.txt","r")
    lines = len(products_url_txt.readlines())
    
    start_index = 0        
    
    for i in range(THREAD_COUNT):
        end_index = start_index + math.ceil(lines / THREAD_COUNT)
        if end_index > lines + 1: end_index = lines + 1
        if i == thread_index :
            th = TotalImports_Thread(i, start_index, end_index, stock_scrape)
            th.start()
            if thread_index < len(t_totalimports):
                t_totalimports[thread_index] = th
                t_totalimports_delay[thread_index] = 0
            else:
                t_totalimports.append(th)
                t_totalimports_delay.append(0)
            break

        start_index = end_index


def totalimports_scrape(stock_scrape=0):
    for i in range(THREAD_COUNT):
        totalimports_thread_start(i, stock_scrape)


def origo_category_scrape(stock_scrape=0):
    global t_origo_cat, t_origo
    t_origo_cat = Origo_Category_Thread(stock_scrape)
    t_origo_cat.start()


def origo_scrape(stock_scrape=0):
    global t_origo
    products_url_txt = open("origo_products_url.txt","r")
    lines = len(products_url_txt.readlines())
    
    start_index = 0        
    
    for i in range(THREAD_COUNT):
        end_index = start_index + math.ceil(lines / THREAD_COUNT)
        if end_index > lines + 1: end_index = lines + 1
        th = RDS_Thread(i, start_index, end_index, stock_scrape)
        th.start()
        t_origo.append(th)

        start_index = end_index