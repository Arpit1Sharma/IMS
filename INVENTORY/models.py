from django.db import models

class Categorie(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
class Item(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Categorie, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    time = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.name}"
class Transaction(models.Model):
    REASON_CHOICES = [
        ('sold', 'Sold'),
        ('defective', 'Defective'),
        ('added', 'Added'),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    change = models.IntegerField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)

    def __str__(self):
        return f"{self.item.name} | {self.change} | {self.reason}"
    
class SoldItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name if self.item else 'Unknown'} - {self.quantity} sold on {self.date}"
    
class DefectiveItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name if self.item else 'Unknown'} - {self.quantity} marked defective on {self.date}"

class Stock(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(Categorie, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.name} - {self.quantity} in stock"