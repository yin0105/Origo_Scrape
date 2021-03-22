# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.forms.utils import ErrorList
from django.http import HttpResponse
from .origo import Origo_Thread
from os.path import join, dirname
from .origo import scrape_status as origo_scrape_status
import glob, os


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
