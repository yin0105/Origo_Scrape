from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static

from main.views import IndexPageView, ChangeLanguageView
from origo_scrape import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # path('', IndexPageView.as_view(), name='index'),
    path('', views.index, name="index"),

    path('i18n/', include('django.conf.urls.i18n')),
    path('language/', ChangeLanguageView.as_view(), name='change_language'),

    path('accounts/', include('accounts.urls')),

    
    path('start_scrape/', views.start_scrape, name="start_scrape"),
    path('get_scraping_status/', views.get_scraping_status, name="get_scraping_status"),
    path('get_xls_list/', views.get_xls_list, name="get_xls_list"),
    path('download', views.download, name="download"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
