from django.urls import path
# from .views import index, start_scrape, get_scraping_status, get_xls_list, download
from origo_scrape import views

urlpatterns = [
    path('', views.index, name="home"),
    path('start_scrape/', views.start_scrape, name="start_scrape"),
    path('get_scraping_status/', views.get_scraping_status, name="get_scraping_status"),
    path('get_xls_list/', views.get_xls_list, name="get_xls_list"),
    path('download', views.download, name="download"),
    # path('stores/',stores_views.detail,{'location':'headquarters'})
    # path('start_scrape/<str:scrape_type>/<str:site>', start_scrape, name="start_scrape"),
    # path('register/', register_user, name="register"),
    # path("logout/", LogoutView.as_view(), name="logout")
]
