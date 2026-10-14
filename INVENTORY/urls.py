from django.urls import path
from . import views
urlpatterns = [
    path('',views.index,name="Inventory"),
    path('add/',views.add_item,name="add_item"),
    path('remove/', views.remove_item, name='remove_item'),
    path('sold/',views.sold_item,name="sold_item"),
    path('defective/',views.defective_item,name="defective_item"),
    path('report/', views.inventory_report, name='inventory_report'),
    path('report/pdf/', views.generate_inventory_pdf, name='generate_inventory_pdf'),
]