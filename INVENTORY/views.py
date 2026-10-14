from django.shortcuts import render,redirect
from django.http import HttpResponse
from .forms import ItemForm, RemoveItemForm
from .models import Item, Transaction,SoldItem, DefectiveItem,Stock
from django.db.models import Sum
from django.db import transaction as db_transaction
from django.contrib import messages
from collections import defaultdict
from django.utils import timezone
from datetime import datetime,timedelta
from django.contrib.auth.forms import UserCreationForm
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt
from io import BytesIO
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'home.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully! You can now login.")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
@never_cache
def index(request):
    filter_type = request.GET.get('filter', 'all')  # default 'all'
    today = timezone.now()
    if filter_type == 'daily':
        start_date = today.date()
        sold_items = SoldItem.objects.filter(date=start_date)
        defective_items = DefectiveItem.objects.filter(date=start_date)
    elif filter_type == 'weekly':
        start_week = today - timedelta(days=today.weekday())  # start of this week
        sold_items = SoldItem.objects.filter(date__gte=start_week.date())
        defective_items = DefectiveItem.objects.filter(date__gte=start_week.date())
    elif filter_type == 'monthly':
        sold_items = SoldItem.objects.filter(date__year=today.year, date__month=today.month)
        defective_items = DefectiveItem.objects.filter(date__year=today.year, date__month=today.month)
    else:  # 'all'
        sold_items = SoldItem.objects.all()
        defective_items = DefectiveItem.objects.all()
    stocks = Stock.objects.all()
    category_data = defaultdict(int)
    for stock in stocks:
        category_data[stock.category.name] += stock.quantity
    categories = list(category_data.keys())
    quantities = list(category_data.values())
    sold_item_data = defaultdict(int)
    for item in sold_items:
        sold_item_data[item.item.category.name] += item.quantity
    sold_categories = list(sold_item_data.keys())
    sold_quantities = list(sold_item_data.values())
    defective_item_data = defaultdict(int)
    for item in defective_items:
        defective_item_data[item.item.category.name] += item.quantity
    defective_categories = list(defective_item_data.keys())
    defective_quantities = list(defective_item_data.values())
    context = {
        'stocks': stocks,
        'categories': categories,
        'quantities': quantities,
        'sold_categories': sold_categories,
        'sold_quantities': sold_quantities,
        'defective_categories': defective_categories,
        'defective_quantities': defective_quantities,
        'filter_type': filter_type,
    }
    return render(request, 'INVENTORY/index.html', context)

@login_required
@never_cache
@db_transaction.atomic
def add_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            stock, created = Stock.objects.get_or_create(
                name=item.name,
                defaults={'category': item.category, 'quantity': item.quantity}
            )
            if not created:
                stock.quantity += item.quantity
                stock.save()
            Transaction.objects.create(item=item, change=item.quantity, reason='added')
            messages.success(request, 'Item added successfully.')
            return redirect('add_item')
    else:
        form = ItemForm()
    filter_type = request.GET.get('filter', 'all')
    now = timezone.now()
    if filter_type == 'daily':
        items = Item.objects.filter(time__date=now.date()).order_by('-time')
    elif filter_type == 'weekly':
        start_week = now - timedelta(days=now.weekday())
        items = Item.objects.filter(time__date__gte=start_week.date()).order_by('-time')
    elif filter_type == 'monthly':
        items = Item.objects.filter(time__year=now.year, time__month=now.month).order_by('-time')
    else:
        items = Item.objects.all().order_by('-time')
    today_count = Item.objects.filter(time__date=now.date()).count()
    start_week = now - timedelta(days=now.weekday())
    week_count = Item.objects.filter(time__date__gte=start_week.date()).count()
    month_count = Item.objects.filter(time__year=now.year, time__month=now.month).count()
    return render(request, 'INVENTORY/add_item.html', {
        'form': form,
        'items': items,
        'filter_type': filter_type,
        'today_count': today_count,
        'week_count': week_count,
        'month_count': month_count,
    })

@login_required
@never_cache
@db_transaction.atomic
def remove_item(request):
    if request.method == 'POST':
        form = RemoveItemForm(request.POST)
        if form.is_valid():
            item_name = form.cleaned_data['item_name']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']
            try:
                stock = Stock.objects.get(name=item_name)
            except Stock.DoesNotExist:
                messages.error(request, 'Item not found in stock.')
                return redirect('remove_item')
            if stock.quantity < quantity:
                messages.error(request, 'Not enough quantity in stock.')
                return redirect('remove_item')
            stock.quantity -= quantity
            stock.save()
            remaining = quantity
            items = Item.objects.filter(name=item_name).order_by('time')
            for item in items:
                if remaining == 0:
                    break
                deduct = min(item.quantity, remaining)
                Transaction.objects.create(item=item, change=-deduct, reason=reason)
                if reason == 'sold':
                    SoldItem.objects.create(item=item, quantity=deduct)
                elif reason == 'defective':
                    DefectiveItem.objects.create(item=item, quantity=deduct)

                remaining -= deduct

            messages.success(request, f'{quantity} {item_name}(s) removed as {reason}.')
            return redirect('remove_item')
    else:
        form = RemoveItemForm()
    return render(request, 'INVENTORY/remove_item.html', {'form': form})

@login_required
@never_cache
def sold_item(request):
    now = timezone.now()
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'daily':
        sold_items = SoldItem.objects.select_related('item').filter(date__date=now.date()).order_by('-date')
    elif filter_type == 'weekly':
        start_week = now - timedelta(days=now.weekday())
        sold_items = SoldItem.objects.select_related('item').filter(date__date__gte=start_week.date()).order_by('-date')
    elif filter_type == 'monthly':
        sold_items = SoldItem.objects.select_related('item').filter(date__year=now.year, date__month=now.month).order_by('-date')
    else:
        sold_items = SoldItem.objects.select_related('item').order_by('-date')
    today_count = SoldItem.objects.filter(date__date=now.date()).count()
    start_week = now - timedelta(days=now.weekday())
    week_count = SoldItem.objects.filter(date__date__gte=start_week.date()).count()
    month_count = SoldItem.objects.filter(date__year=now.year, date__month=now.month).count()
    return render(request, 'INVENTORY/sold_item.html', {
        'sold_items': sold_items,
        'filter_type': filter_type,
        'today_count': today_count,
        'week_count': week_count,
        'month_count': month_count,
    })

@login_required
@never_cache
def defective_item(request):
    now = timezone.now()
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'daily':
        defective_items = DefectiveItem.objects.select_related('item').filter(date__date=now.date()).order_by('-date')
    elif filter_type == 'weekly':
        start_week = now - timedelta(days=now.weekday())
        defective_items = DefectiveItem.objects.select_related('item').filter(date__date__gte=start_week.date()).order_by('-date')
    elif filter_type == 'monthly':
        defective_items = DefectiveItem.objects.select_related('item').filter(date__year=now.year, date__month=now.month).order_by('-date')
    else:
        defective_items = DefectiveItem.objects.select_related('item').order_by('-date')
    today_count = DefectiveItem.objects.filter(date__date=now.date()).count()
    start_week = now - timedelta(days=now.weekday())
    week_count = DefectiveItem.objects.filter(date__date__gte=start_week.date()).count()
    month_count = DefectiveItem.objects.filter(date__year=now.year, date__month=now.month).count()
    return render(request, 'INVENTORY/defective_item.html', {
        'defective_items': defective_items,
        'filter_type': filter_type,
        'today_count': today_count,
        'week_count': week_count,
        'month_count': month_count,
    })

@login_required
@never_cache
def inventory_report(request):
    filter_type = request.GET.get('filter', 'all')
    today = datetime.today().date()
    if filter_type == 'daily':
        item_names = Item.objects.filter(time__date=today).values_list('name', flat=True).distinct()
        sold_items = SoldItem.objects.filter(date__date=today).select_related('item')
        defective_items = DefectiveItem.objects.filter(date__date=today).select_related('item')
    elif filter_type == 'weekly':
        start_week = today - timedelta(days=today.weekday())
        item_names = Item.objects.filter(time__date__range=[start_week, today]).values_list('name', flat=True).distinct()
        sold_items = SoldItem.objects.filter(date__date__range=[start_week, today]).select_related('item')
        defective_items = DefectiveItem.objects.filter(date__date__range=[start_week, today]).select_related('item')
    elif filter_type == 'monthly':
        item_names = Item.objects.filter(time__year=today.year, time__month=today.month).values_list('name', flat=True).distinct()
        sold_items = SoldItem.objects.filter(date__year=today.year, date__month=today.month).select_related('item')
        defective_items = DefectiveItem.objects.filter(date__year=today.year, date__month=today.month).select_related('item')
    else:
        item_names = Stock.objects.values_list('name', flat=True)
        sold_items = SoldItem.objects.all().select_related('item')
        defective_items = DefectiveItem.objects.all().select_related('item')
    stocks = Stock.objects.filter(name__in=item_names)
    def get_category_data(queryset, via_item=False):
       if via_item:
           category_data = queryset.values('item__category__name').annotate(total=Sum('quantity'))
           labels = [entry['item__category__name'] for entry in category_data]
       else:
           category_data = queryset.values('category__name').annotate(total=Sum('quantity'))
           labels = [entry['category__name'] for entry in category_data]
    
       quantities = [entry['total'] for entry in category_data]
       return labels, quantities
    stock_labels, stock_quantities = get_category_data(stocks, via_item=False)
    sold_labels, sold_quantities = get_category_data(sold_items, via_item=True)
    defective_labels, defective_quantities = get_category_data(defective_items, via_item=True)
    context = {
    'stocks': stocks,
    'filter_type': filter_type,
    'categories': stock_labels,
    'quantities': stock_quantities,
    'sold_categories': sold_labels,
    'sold_quantities': sold_quantities,
    'defective_categories': defective_labels,
    'defective_quantities': defective_quantities,
    'sold_items': sold_items,
    'defective_items': defective_items,
    }
    return render(request, 'INVENTORY/inventory_report.html', context)

@login_required
@never_cache
def generate_inventory_pdf(request):
    filter_type = request.GET.get('filter', 'all')
    today = datetime.today().date()
    if filter_type == 'daily':
        item_names = Item.objects.filter(time__date=today).values_list('name', flat=True).distinct()
        sold_items = SoldItem.objects.filter(date__date=today).select_related('item')
        defective_items = DefectiveItem.objects.filter(date__date=today).select_related('item')
    elif filter_type == 'weekly':
        start_week = today - timedelta(days=today.weekday())
        item_names = Item.objects.filter(time__date__range=[start_week, today]).values_list('name', flat=True).distinct()
        sold_items = SoldItem.objects.filter(date__date__range=[start_week, today]).select_related('item')
        defective_items = DefectiveItem.objects.filter(date__date__range=[start_week, today]).select_related('item')
    elif filter_type == 'monthly':
        item_names = Item.objects.filter(time__year=today.year, time__month=today.month).values_list('name', flat=True).distinct()
        sold_items = SoldItem.objects.filter(date__year=today.year, date__month=today.month).select_related('item')
        defective_items = DefectiveItem.objects.filter(date__year=today.year, date__month=today.month).select_related('item')
    else:
        item_names = Stock.objects.values_list('name', flat=True)
        sold_items = SoldItem.objects.all().select_related('item')
        defective_items = DefectiveItem.objects.all().select_related('item')
    stocks = Stock.objects.filter(name__in=item_names)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="inventory_report_{filter_type}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    def add_section_title(title):
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b>{title}</b>", styles['Heading3']))
        elements.append(Spacer(1, 6))
    def create_table(data, col_widths):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        return table
    def generate_bar_chart(title, labels, quantities):
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.bar(labels, quantities, color='skyblue')
        ax.set_title(title)
        ax.set_ylabel('Quantity')
        plt.xticks(rotation=45, ha='right')
        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='PNG')
        plt.close(fig)
        buf.seek(0)
        return Image(buf, width=400, height=200)

    def get_category_data(queryset, via_item=False):
        if via_item:
            data = queryset.values('item__category__name').annotate(total=Sum('quantity'))
            labels = [d['item__category__name'] for d in data]
        else:
            data = queryset.values('category__name').annotate(total=Sum('quantity'))
            labels = [d['category__name'] for d in data]
        quantities = [d['total'] or 0 for d in data]
        return labels, quantities
    elements.append(Paragraph(f"<b>Inventory Report - {filter_type.capitalize()}</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    add_section_title("Current Stock")
    stock_data = [['Sr No', 'Item Name', 'Category', 'Quantity']]
    for i, stock in enumerate(stocks, 1):
        stock_data.append([str(i), stock.name, stock.category.name, str(stock.quantity)])
    if len(stock_data) == 1:
        stock_data.append(['-', 'No Data', '-', '-'])
    elements.append(create_table(stock_data, [40, 180, 150, 80]))
    elements.append(Spacer(1, 12))
    stock_labels, stock_quantities = get_category_data(stocks)
    if stock_labels:
        elements.append(generate_bar_chart("Stock Distribution by Category", stock_labels, stock_quantities))
    add_section_title("Sold Items")
    sold_data = [['Sr No', 'Item Name', 'Category', 'Quantity', 'Date']]
    for i, s in enumerate(sold_items, 1):
        sold_data.append([str(i), s.item.name, s.item.category.name, str(s.quantity), s.date.strftime('%Y-%m-%d')])
    if len(sold_data) == 1:
        sold_data.append(['-', 'No Data', '-', '-', '-'])
    elements.append(create_table(sold_data, [40, 150, 150, 80, 80]))
    elements.append(Spacer(1, 12))
    sold_labels, sold_quantities = get_category_data(sold_items, via_item=True)
    if sold_labels:
        elements.append(generate_bar_chart("Sold Items by Category", sold_labels, sold_quantities))
    add_section_title("Defective Items")
    defective_data = [['Sr No', 'Item Name', 'Category', 'Quantity', 'Date']]
    for i, d in enumerate(defective_items, 1):
        defective_data.append([str(i), d.item.name, d.item.category.name, str(d.quantity), d.date.strftime('%Y-%m-%d')])
    if len(defective_data) == 1:
        defective_data.append(['-', 'No Data', '-', '-', '-'])
    elements.append(create_table(defective_data, [40, 150, 150, 80, 80]))
    elements.append(Spacer(1, 12))
    defective_labels, defective_quantities = get_category_data(defective_items, via_item=True)
    if defective_labels:
        elements.append(generate_bar_chart("Defective Items by Category", defective_labels, defective_quantities))
    doc.build(elements)
    return response