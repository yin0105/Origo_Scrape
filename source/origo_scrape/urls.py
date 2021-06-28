from origo_scrape import views
from django.contrib import admin
from django.urls import path, include, re_path
from django.views import generic, static
from django.conf.urls import url
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),
    
    # path('home', views.index, name="home"),
    # path('start_scrape/', views.start_scrape, name="start_scrape"),
    # path('get_scraping_status/', views.get_scraping_status, name="get_scraping_status"),
    # path('get_xls_list/', views.get_xls_list, name="get_xls_list"),
    # path('download', views.download, name="download"),

    re_path(r'.*', generic.TemplateView.as_view(template_name='index.html')),
    url(r'^static/(?P<path>.*)$', static.serve,
      {'document_root': settings.STATIC_ROOT}, name='static'),

]
