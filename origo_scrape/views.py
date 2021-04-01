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
from os.path import join, dirname
# from .origo import scrape_status as origo_scrape_status
import glob, os, zipfile, openpyxl, xlsxwriter
from os import path

# from filewrap import Filewrapper


# dotenv_path = join(dirname(__file__), '.env')
# load_dotenv(dotenv_path)
cur_path = dirname(__file__)
root_path = cur_path[:cur_path.rfind(os.path.sep)]
# root_path = root_path[:root_path.rfind(os.path.sep)]
cur_site = ""
# t_origo = ""
# t_supply_it = ""
# t_ff = ""
sites = [{"url": "https://origo-online.origo.ie", "short": "origo"}, {"url": "https://www.supply-it.ie/", "short": "supply_it"}, {"url": "https://online.furlongflooring.com/", "short": "furlongflooring"}]
def index(request):
    global sites
    # return render(request, "index.html")
    context = {}
    context['sites'] = sites
    html_template = loader.get_template( 'index.html' )
    return HttpResponse(html_template.render(context, request))


def start_scrape(request):
    global t_origo, t_supply_it, t_ff, cur_site

    print("start_scrape")
    cur_site = request.GET["site"]
    scrape_type = request.GET["scrape_type"]
    if cur_site == "origo":
        t_origo = Origo_Thread(scrape_type)
        t_origo.start()
    elif cur_site == "supply_it":
        t_supply_it = Supply_it_Thread(scrape_type)
        t_supply_it.start()
    elif cur_site == "furlongflooring":
        t_ff = FF_Thread(scrape_type)
        t_ff.start()

    return HttpResponse(root_path)


def get_scraping_status(request):
    global t_origo, t_supply_it, t_ff
    res = ""
    cur_site = request.GET["site"]

    if cur_site == "origo" :
        res = t_origo.status
    elif cur_site == "supply_it" :
        res = t_supply_it.status
    elif cur_site == "furlongflooring" :
        res = t_ff.status
        # res = origo_scrape_status
    # if cur_site == "supply_it" :
    #     res = supply_it_scrape_status
    # if cur_site == "furlongflooring" :
    #     res = furlongflooring_scrape_status
        
    
    return HttpResponse(res)
    

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


# path('download/<int:stock>/<int:diff>/<string:recent>/<string:compare>
# def download(request):
#     file_name = "products"
#     if request.GET["stock"] == 1 : file_name = "stock"
#     if request.GET["diff"] == 1 : file_name += "-diff"
#     file_path = os.path.join(root_path, "xls", file_name + ".xlsx")
#     if os.path.exists(file_path):
#         with open(file_path, 'rb', encoding="utf-8") as fh:
#             response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
#             response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
#             return response
#     raise HttpResponse("")

# def register_user(request):

#     msg     = None
#     success = False

#     if request.method == "POST":
#         form = SignUpForm(request.POST)
#         if form.is_valid():
#             form.save()
#             username = form.cleaned_data.get("username")
#             raw_password = form.cleaned_data.get("password1")
#             user = authenticate(username=username, password=raw_password)

#             msg     = 'User created - please <a href="/login">login</a>.'
#             success = True
            
#             #return redirect("/login/")

#         else:
#             msg = 'Form is not valid'    
#     else:
#         form = SignUpForm()

#     return render(request, "accounts/register.html", {"form": form, "msg" : msg, "success" : success })
