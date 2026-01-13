# Generated migration for enhanced features

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('smartcity_app', '0008_wastebin_image'),
    ]

    operations = [
        # WasteTask model
        migrations.CreateModel(
            name='WasteTask',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('ASSIGNED', 'Assigned'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed'), ('REJECTED', 'Rejected'), ('TIMEOUT', 'Timeout')], default='PENDING', max_length=20)),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('URGENT', 'Urgent')], default='MEDIUM', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_at', models.DateTimeField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('estimated_duration', models.IntegerField(default=30, help_text='Estimated duration in minutes')),
                ('actual_duration', models.IntegerField(blank=True, help_text='Actual duration in minutes', null=True)),
                ('assigned_truck', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='smartcity_app.truck')),
                ('waste_bin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='smartcity_app.wastebin')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # RouteOptimization model
        migrations.CreateModel(
            name='RouteOptimization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('waypoints', models.JSONField(help_text='List of bin IDs in optimal order')),
                ('total_distance', models.FloatField(help_text='Total distance in kilometers')),
                ('estimated_time', models.IntegerField(help_text='Estimated time in minutes')),
                ('fuel_estimate', models.FloatField(help_text='Estimated fuel consumption in liters')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('truck', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routes', to='smartcity_app.truck')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # AlertNotification model
        migrations.CreateModel(
            name='AlertNotification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('alert_type', models.CharField(choices=[('WASTE_BIN_FULL', 'Waste Bin Full'), ('TEMPERATURE_CRITICAL', 'Temperature Critical'), ('HUMIDITY_CRITICAL', 'Humidity Critical'), ('DEVICE_OFFLINE', 'Device Offline'), ('TASK_TIMEOUT', 'Task Timeout'), ('FUEL_LOW', 'Fuel Low'), ('MAINTENANCE_DUE', 'Maintenance Due'), ('ENERGY_SPIKE', 'Energy Spike')], max_length=30)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('severity', models.CharField(choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('CRITICAL', 'Critical')], default='INFO', max_length=20)),
                ('channel', models.CharField(choices=[('APP', 'In-App'), ('SMS', 'SMS'), ('EMAIL', 'Email'), ('TELEGRAM', 'Telegram'), ('PUSH', 'Push Notification')], default='APP', max_length=20)),
                ('recipient', models.CharField(help_text='Phone number, email, or user ID', max_length=255)),
                ('is_sent', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('related_facility', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='smartcity_app.facility')),
                ('related_truck', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='smartcity_app.truck')),
                ('related_waste_bin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='smartcity_app.wastebin')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # ClimateSchedule model
        migrations.CreateModel(
            name='ClimateSchedule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Schedule name', max_length=255)),
                ('days_of_week', models.JSONField(help_text="List of active days ['MON', 'TUE', ...]")),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('action', models.CharField(choices=[('INCREASE_TEMP', 'Increase Temperature'), ('DECREASE_TEMP', 'Decrease Temperature'), ('MAINTAIN_TEMP', 'Maintain Temperature'), ('INCREASE_HUMIDITY', 'Increase Humidity'), ('DECREASE_HUMIDITY', 'Decrease Humidity'), ('SHUTDOWN', 'Shutdown')], max_length=30)),
                ('target_temperature', models.FloatField(blank=True, null=True)),
                ('target_humidity', models.FloatField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('boiler', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='smartcity_app.boiler')),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='smartcity_app.facility')),
            ],
            options={
                'ordering': ['start_time'],
            },
        ),
        
        # EnergyReport model
        migrations.CreateModel(
            name='EnergyReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('report_type', models.CharField(choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly'), ('YEARLY', 'Yearly')], max_length=20)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('total_energy_kwh', models.FloatField(help_text='Total energy consumed in kWh')),
                ('total_cost', models.FloatField(help_text='Total cost in local currency')),
                ('average_temperature', models.FloatField()),
                ('average_humidity', models.FloatField()),
                ('efficiency_score', models.FloatField(help_text='0-100 score')),
                ('cost_savings', models.FloatField(default=0, help_text='Savings compared to previous period')),
                ('recommendations', models.TextField(blank=True)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('generated_by', models.CharField(default='SYSTEM', max_length=100)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='energy_reports', to='smartcity_app.facility')),
            ],
            options={
                'ordering': ['-generated_at'],
            },
        ),
        
        # WastePrediction model
        migrations.CreateModel(
            name='WastePrediction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('prediction_date', models.DateField()),
                ('predicted_fill_level', models.IntegerField(help_text='Predicted fill level 0-100')),
                ('confidence', models.FloatField(help_text='Prediction confidence 0-100')),
                ('will_be_full', models.BooleanField(default=False)),
                ('recommended_collection_date', models.DateField(blank=True, null=True)),
                ('based_on_data_points', models.IntegerField(help_text='Number of historical data points used')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('waste_bin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='predictions', to='smartcity_app.wastebin')),
            ],
            options={
                'ordering': ['-prediction_date'],
            },
        ),
        
        # MaintenanceSchedule model
        migrations.CreateModel(
            name='MaintenanceSchedule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('scheduled_date', models.DateField()),
                ('completion_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('SCHEDULED', 'Scheduled'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled'), ('OVERDUE', 'Overdue')], default='SCHEDULED', max_length=20)),
                ('task_description', models.TextField()),
                ('assigned_technician', models.CharField(blank=True, max_length=100)),
                ('notes', models.TextField(blank=True)),
                ('estimated_cost', models.FloatField(blank=True, null=True)),
                ('actual_cost', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('boiler', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='maintenance_schedules', to='smartcity_app.boiler')),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='maintenance_schedules', to='smartcity_app.facility')),
            ],
            options={
                'ordering': ['scheduled_date'],
            },
        ),
        
        # DriverPerformance model
        migrations.CreateModel(
            name='DriverPerformance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('bins_collected', models.IntegerField(default=0)),
                ('total_distance', models.FloatField(default=0, help_text='km')),
                ('total_time', models.IntegerField(default=0, help_text='minutes')),
                ('fuel_used', models.FloatField(default=0, help_text='liters')),
                ('tasks_completed', models.IntegerField(default=0)),
                ('tasks_rejected', models.IntegerField(default=0)),
                ('average_response_time', models.IntegerField(default=0, help_text='Average time to accept task in seconds')),
                ('rating', models.FloatField(default=5.0, help_text='Performance rating 1-5')),
                ('truck', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='performance_records', to='smartcity_app.truck')),
            ],
            options={
                'ordering': ['-date'],
                'unique_together': {('truck', 'date')},
            },
        ),
    ]
