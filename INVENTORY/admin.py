from django.contrib import admin
from .models import Categorie, Item, Transaction, SoldItem, DefectiveItem, Stock

@admin.register(Categorie)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'quantity']
    list_filter = ['category']
    search_fields = ['name']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'item', 'date', 'change', 'reason']
    list_filter = ['reason', 'date']
    search_fields = ['item__name']

@admin.register(SoldItem)
class SoldItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'item', 'quantity', 'date']
    list_filter = ['date']
    search_fields = ['item__name']

@admin.register(DefectiveItem)
class DefectiveItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'item', 'quantity', 'date']
    list_filter = ['date']
    search_fields = ['item__name']

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'quantity']
    list_filter = ['category']
    search_fields = ['name']
