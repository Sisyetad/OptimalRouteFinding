from django.db import models

class FuelStationModel(models.Model):
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    retail_price = models.DecimalField(max_digits=6, decimal_places=3)
    latitude = models.FloatField()
    longitude = models.FloatField() 
    h3_index = models.CharField(max_length=15, db_index=True, blank=True)
    
    class Meta:
        db_table = 'fuel_stations'
        unique_together = ("truckstop_name", "address", "city", "state")
        indexes = [
            models.Index(fields=['state']),
            models.Index(fields=['retail_price']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['h3_index']),
        ]

    def __str__(self):
        return f"{self.truckstop_name} ({self.state}) - ${self.retail_price}"
