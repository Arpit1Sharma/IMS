from django import forms
from .models import Item
from django.db.models import Sum

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'category', 'quantity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Item Name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Enter Quantity'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = "Select Category"
        self.fields['quantity'].empty_label = "Enter Quantity"
        self.fields['quantity'].min_value = 1


REASON_CHOICES = [
    ('sold', 'Sold'),
    ('defective', 'Defective'),
]

class RemoveItemForm(forms.Form):
    item_name = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Quantity'})
    )
    reason = forms.ChoiceField(
        choices=REASON_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        item_names = Item.objects.values('name').annotate(total=Sum('quantity')).filter(total__gt=0)
        self.fields['item_name'].choices = [
            (item['name'], f"{item['name']}") for item in item_names
        ]
        self.fields['item_name'].empty_label = "Select Item"
        self.fields['reason'].empty_label = "Select Reason"