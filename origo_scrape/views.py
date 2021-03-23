# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.forms.utils import ErrorList
from django.http import HttpResponse
from .origo import Origo_Thread
from os.path import join, dirname
from .origo import scrape_status as origo_scrape_status
import glob, os, zipfile
# from filewrap import Filewrapper


# dotenv_path = join(dirname(__file__), '.env')
# load_dotenv(dotenv_path)
cur_path = dirname(__file__)
root_path = cur_path[:cur_path.rfind("\\")]
cur_site = ""

def index(request):
    return render(request, "index.html")


def start_scrape(request):
    global t, cur_site
    print("start_scrape")
    cur_site = request.GET["site"]
    scrape_type = request.GET["scrape_type"]
    if cur_site == "origo":
        t = Origo_Thread(scrape_type)
    t.start()

    return HttpResponse("ok")


def get_scraping_status(request):
    res = ""
    if cur_site == "origo" :
        res = origo_scrape_status
        res = t.status
    
    return HttpResponse(res)
    

def get_xls_list(request):
    global root_path
    products_arr = []
    stock_arr = []
    res = ""
    for file in glob.glob(join(root_path, "xls", "products-*.xlsx")):
        products_arr.append(file[file.rfind(os.path.sep) + 10 : -5])
    for file in glob.glob(join(root_path, "xls", "stock-*.xlsx")):
        stock_arr.append(file[file.rfind(os.path.sep) + 7 : -5])
    products_arr.sort(reverse=True)
    stock_arr.sort(reverse=True)
    res = '{"full": "' + '_'.join(products_arr) + '", "stock": "' + '_'.join(stock_arr) + '"}'
    
    return HttpResponse(res)


def download(request):
    file_name = "products"
    print(request.GET["stock"])
    if request.GET["stock"] == "1" : file_name = "stock"
    if request.GET["diff"] == "1" : file_name += "-diff"
    file_name += "-" + request.GET["recent"]
    if request.GET["diff"] == "1" : file_name += "_" + request.GET["compare"]
    # file_name = "products-2021-0320-020256"
    file_name += ".xlsx"
    print("file_name = " + file_name)

    file_path = os.path.join(root_path, "xls", file_name)
    print("file_path = " + file_path)

    response = HttpResponse(content_type='application/zip')
    zf = zipfile.ZipFile(response, 'w')

    with open(file_path, 'rb') as fh:
        zf.writestr(file_name, fh.read())

    # return as zipfile
    response['Content-Disposition'] = f'attachment; filename={file_name + ".zip"}'
    return response


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
