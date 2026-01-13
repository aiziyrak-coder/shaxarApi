from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from uuid import uuid4
import uuid


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Add any additional user fields here if needed
    
    # Override the groups and user_permissions fields to avoid conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='smartcity_user_set',  # Use a custom related_name
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='smartcity_user_set',  # Use a custom related_name
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )


class Coordinate(models.Model):
    id = models.AutoField(primary_key=True)
    lat = models.FloatField()
    lng = models.FloatField()

    def __str__(self):
        return f"({self.lat}, {self.lng})"


class Region(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    center = models.OneToOneField(Coordinate, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class District(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    center = models.OneToOneField(Coordinate, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Organization(models.Model):
    ORGANIZATION_TYPES = [
        ('HOKIMIYAT', 'Hokimiyat'),
        ('AGENCY', 'Agency'),
        ('ENTERPRISE', 'Enterprise'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=ORGANIZATION_TYPES)
    login = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)  # In production, use Django's password hashing
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    center = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    enabled_modules = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class DeviceHealth(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    battery_level = models.FloatField()
    signal_strength = models.FloatField()
    last_ping = models.DateTimeField()
    firmware_version = models.CharField(max_length=50)
    is_online = models.BooleanField(default=True)

    def __str__(self):
        return f"Device Health - Online: {self.is_online}"


class WasteBin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='waste_bins')
    address = models.CharField(max_length=500)
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    toza_hudud = models.CharField(max_length=50, default='1-sonli Toza Hudud')
    camera_url = models.URLField(blank=True, null=True)
    google_maps_url = models.URLField(blank=True, null=True)
    fill_level = models.IntegerField(default=0)
    fill_rate = models.FloatField(default=1.5)
    last_analysis = models.CharField(max_length=200, default='Yangi qo\'shildi')
    image_url = models.URLField(blank=True, null=True)
    image_source = models.CharField(max_length=20, default='CCTV')
    is_full = models.BooleanField(default=False)
    device_health = models.JSONField(default=dict)
    qr_code_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='waste_bin_images/', blank=True, null=True)


class IoTDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.CharField(max_length=100, unique=True)  # ESP-A4C416
    device_type = models.CharField(max_length=50, choices=[('TEMPERATURE_SENSOR', 'Temperature Sensor'), ('HUMIDITY_SENSOR', 'Humidity Sensor'), ('BOTH', 'Temperature and Humidity Sensor')])
    room = models.ForeignKey('Room', on_delete=models.CASCADE, null=True, blank=True, related_name='iot_devices')
    boiler = models.ForeignKey('Boiler', on_delete=models.CASCADE, null=True, blank=True, related_name='iot_devices')
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Current sensor readings
    current_temperature = models.FloatField(null=True, blank=True)
    current_humidity = models.FloatField(null=True, blank=True)
    last_sensor_update = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.device_id} - {self.device_type}"


class Truck(models.Model):
    TRUCK_STATUS_CHOICES = [
        ('IDLE', 'Idle'),
        ('BUSY', 'Busy'),
        ('OFFLINE', 'Offline'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='trucks')
    driver_name = models.CharField(max_length=255)
    plate_number = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    toza_hudud = models.CharField(max_length=50, default='1-sonli Toza Hudud')
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=TRUCK_STATUS_CHOICES, default='IDLE')
    fuel_level = models.IntegerField(default=100)
    login = models.CharField(max_length=150)
    password = models.CharField(max_length=128)  # In production, use Django's password hashing
    
    def __str__(self):
        return f"Truck {self.plate_number} - {self.driver_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class MoistureSensor(models.Model):
    SENSOR_STATUS_CHOICES = [
        ('OPTIMAL', 'Optimal'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    mfy = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=SENSOR_STATUS_CHOICES)
    moisture_level = models.FloatField()
    last_update = models.DateTimeField()

    def __str__(self):
        return f"Moisture Sensor {self.mfy}"


class Facility(models.Model):
    FACILITY_TYPE_CHOICES = [
        ('SCHOOL', 'School'),
        ('KINDERGARTEN', 'Kindergarten'),
        ('HOSPITAL', 'Hospital'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=FACILITY_TYPE_CHOICES)
    mfy = models.CharField(max_length=100)
    overall_status = models.CharField(max_length=20, choices=MoistureSensor.SENSOR_STATUS_CHOICES)
    energy_usage = models.FloatField()
    efficiency_score = models.FloatField()
    manager_name = models.CharField(max_length=100)
    last_maintenance = models.DateTimeField()
    history = models.JSONField()  # Stores history as a list of values
    boilers = models.ManyToManyField('Boiler', related_name='facilities')

    def __str__(self):
        return self.name


class Room(models.Model):
    # ID field changed to CharField to support custom IDs like "0420101" (preserves leading zeros)
    id = models.CharField(primary_key=True, max_length=50, unique=True, editable=True, 
                         help_text="Room ID (e.g., 0420101 - leading zeros are preserved)")
    name = models.CharField(max_length=100)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='rooms', null=True, blank=True)
    floor = models.IntegerField(null=True, blank=True)
    capacity = models.IntegerField(null=True, blank=True)
    is_occupied = models.BooleanField(default=False)
    target_humidity = models.FloatField()
    humidity = models.FloatField()
    temperature = models.FloatField(default=22.0)  # Added temperature field
    status = models.CharField(max_length=20, choices=MoistureSensor.SENSOR_STATUS_CHOICES)
    trend = models.JSONField()  # Stores humidity trend as a list of values
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    last_updated = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        if self.facility:
            return f"{self.name} ({self.id}) - {self.facility.name}"
        return f"{self.name} ({self.id})"


class Boiler(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    target_humidity = models.FloatField()
    humidity = models.FloatField()
    temperature = models.FloatField(default=22.0)  # Added temperature field
    status = models.CharField(max_length=20, choices=MoistureSensor.SENSOR_STATUS_CHOICES)
    trend = models.JSONField()  # Stores humidity trend as a list of values
    device_health = models.OneToOneField(DeviceHealth, on_delete=models.CASCADE, related_name='boiler_health')
    connected_rooms = models.ManyToManyField(Room, related_name='boilers')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    last_updated = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name

# Added temperature field d
# sahsdhewisdnd
class AirSensor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    mfy = models.CharField(max_length=100)
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    aqi = models.FloatField()
    pm25 = models.FloatField()
    co2 = models.FloatField()
    status = models.CharField(max_length=20, choices=MoistureSensor.SENSOR_STATUS_CHOICES)

    def __str__(self):
        return self.name


class SOSColumn(models.Model):
    STATUS_CHOICES = [
        ('IDLE', 'Idle'),
        ('ACTIVE', 'Active'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    mfy = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    camera_url = models.URLField()
    last_test = models.DateTimeField()
    device_health = models.OneToOneField(DeviceHealth, on_delete=models.CASCADE)
    
    # Active incident related fields (if any)
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_stress_level = models.FloatField(null=True, blank=True)
    ai_detected_objects = models.JSONField(null=True, blank=True)  # List of detected objects
    ai_keywords = models.JSONField(null=True, blank=True)  # List of keywords

    def __str__(self):
        return self.name


class EcoViolation(models.Model):
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location_name = models.CharField(max_length=255)
    mfy = models.CharField(max_length=100)
    timestamp = models.DateTimeField()
    image_url = models.URLField()
    confidence = models.FloatField()

    # Offender details (optional)
    offender_name = models.CharField(max_length=100, null=True, blank=True)
    face_id = models.CharField(max_length=100, null=True, blank=True)
    face_image_url = models.URLField(null=True, blank=True)
    match_score = models.FloatField(null=True, blank=True)
    estimated_age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"Eco Violation at {self.location_name}"


class ConstructionMission(models.Model):
    CONSTRUCTION_STAGE_CHOICES = [
        ('KOTLOVAN', 'Kotlovan'),
        ('FUNDAMENT', 'Fundament'),
        ('KARKAS_1', 'Karkas 1'),
        ('KARKAS_FULL', 'Karkas Full'),
        ('TOM_YOPISH', 'Tom Yopish'),
        ('PARDOZLASH', 'Pardozlash'),
    ]
    MISSION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('DELAYED', 'Delayed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stage_name = models.CharField(max_length=100)
    stage_type = models.CharField(max_length=20, choices=CONSTRUCTION_STAGE_CHOICES)
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=MISSION_STATUS_CHOICES, default='PENDING')
    progress = models.FloatField()  # 0-100 percentage

    def __str__(self):
        return self.stage_name


class ConstructionSite(models.Model):
    STATUS_CHOICES = [
        ('ON_TRACK', 'On Track'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    contractor_name = models.CharField(max_length=255)
    camera_url = models.URLField()
    start_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    overall_progress = models.FloatField()  # 0-100 percentage
    current_ai_stage = models.CharField(max_length=20, choices=ConstructionMission.CONSTRUCTION_STAGE_CHOICES)
    ai_confidence = models.FloatField()
    detected_objects = models.JSONField()  # {"workers": int, "cranes": int, "trucks": int}
    missions = models.ManyToManyField(ConstructionMission, related_name='construction_sites')

    def __str__(self):
        return self.name


class LightROI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    x = models.FloatField()
    y = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    label = models.CharField(max_length=100)

    def __str__(self):
        return f"ROI {self.label}"


class LightPole(models.Model):
    LIGHT_STATUS_CHOICES = [
        ('ON', 'On'),
        ('OFF', 'Off'),
        ('FLICKERING', 'Flickering'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    camera_url = models.URLField()
    status = models.CharField(max_length=20, choices=LIGHT_STATUS_CHOICES)
    luminance = models.FloatField()
    last_check = models.DateTimeField()
    rois = models.ManyToManyField(LightROI, related_name='light_poles')

    def __str__(self):
        return f"Light Pole at {self.address}"


class Bus(models.Model):
    BUS_STATUS_CHOICES = [
        ('ON_TIME', 'On Time'),
        ('DELAYED', 'Delayed'),
        ('SOS', 'SOS'),
        ('STOPPED', 'Stopped'),
    ]
    DOOR_STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    ]
    DRIVER_FATIGUE_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route_number = models.CharField(max_length=20)
    plate_number = models.CharField(max_length=20)
    driver_name = models.CharField(max_length=100)
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    bearing = models.FloatField()
    speed = models.FloatField()
    rpm = models.FloatField()
    passengers = models.IntegerField()
    status = models.CharField(max_length=20, choices=BUS_STATUS_CHOICES)
    fuel_level = models.FloatField()
    engine_temp = models.FloatField()
    door_status = models.CharField(max_length=20, choices=DOOR_STATUS_CHOICES)
    cabin_temp = models.FloatField()
    driver_fatigue_level = models.CharField(max_length=20, choices=DRIVER_FATIGUE_CHOICES)
    next_stop = models.CharField(max_length=100)
    cctv_urls = models.JSONField()  # {"front": url, "driver": url, "cabin": url}

    def __str__(self):
        return f"Bus {self.route_number} - {self.plate_number}"


class ResponsibleOrg(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    active_brigades = models.IntegerField()
    total_brigades = models.IntegerField()
    current_load = models.FloatField()
    contact_phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class CallRequest(models.Model):
    REQUEST_CATEGORY_CHOICES = [
        ('HEALTH', 'Health'),
        ('INTERIOR', 'Interior'),
        ('WASTE', 'Waste'),
        ('ELECTRICITY', 'Electricity'),
        ('WATER', 'Water'),
        ('GAS', 'Gas'),
        ('OTHER', 'Other'),
    ]
    REQUEST_STATUS_CHOICES = [
        ('NEW', 'New'),
        ('ASSIGNED', 'Assigned'),
        ('PROCESSING', 'Processing'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    citizen_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    transcript = models.TextField()
    category = models.CharField(max_length=20, choices=REQUEST_CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='NEW')
    timestamp = models.DateTimeField()
    address = models.CharField(max_length=255, null=True, blank=True)
    mfy = models.CharField(max_length=100)
    ai_summary = models.TextField()
    keywords = models.JSONField()  # List of keywords
    citizen_trust_score = models.FloatField()
    assigned_org = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')
    deadline = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Call Request from {self.citizen_name}"


class CallRequestTimeline(models.Model):
    """
    Timeline entries for call requests
    """
    TIMELINE_STATUS_CHOICES = [
        ('DONE', 'Done'),
        ('PENDING', 'Pending'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_request = models.ForeignKey(CallRequest, on_delete=models.CASCADE, related_name='timeline')
    step = models.CharField(max_length=100)
    timestamp = models.DateTimeField()
    actor = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=TIMELINE_STATUS_CHOICES)

    def __str__(self):
        return f"Timeline: {self.step} for {self.call_request.id}"


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    read = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')

    def __str__(self):
        return self.title


class ReportEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField()
    mfy = models.CharField(max_length=100)
    location_name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    metric_label = models.CharField(max_length=100)
    value = models.TextField()  # Can store both string and number values
    cost_impact = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=MoistureSensor.SENSOR_STATUS_CHOICES)
    responsible = models.CharField(max_length=100)

    def __str__(self):
        return f"Report: {self.location_name} - {self.metric_label}"


class UtilityNode(models.Model):
    UTILITY_TYPE_CHOICES = [
        ('ELECTRICITY', 'Electricity'),
        ('WATER', 'Water'),
        ('GAS', 'Gas'),
    ]
    NODE_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('WARNING', 'Warning'),
        ('OUTAGE', 'Outage'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=UTILITY_TYPE_CHOICES)
    mfy = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    location = models.OneToOneField(Coordinate, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=NODE_STATUS_CHOICES)
    load = models.FloatField()
    capacity = models.CharField(max_length=50)
    active_tickets = models.IntegerField()

    def __str__(self):
        return f"{self.name} - {self.type}"


# ==================== NEW MODELS FOR ENHANCED FUNCTIONALITY ====================

class WasteTask(models.Model):
    """
    Task assignment for waste collection
    """
    TASK_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('TIMEOUT', 'Timeout'),
    ]
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    waste_bin = models.ForeignKey(WasteBin, on_delete=models.CASCADE, related_name='tasks')
    assigned_truck = models.ForeignKey(Truck, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='PENDING')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    estimated_duration = models.IntegerField(default=30, help_text="Estimated duration in minutes")
    actual_duration = models.IntegerField(null=True, blank=True, help_text="Actual duration in minutes")
    
    def __str__(self):
        return f"Task {self.id} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']


class RouteOptimization(models.Model):
    """
    Optimized routes for waste collection trucks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='routes')
    waypoints = models.JSONField(help_text="List of bin IDs in optimal order")
    total_distance = models.FloatField(help_text="Total distance in kilometers")
    estimated_time = models.IntegerField(help_text="Estimated time in minutes")
    fuel_estimate = models.FloatField(help_text="Estimated fuel consumption in liters")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Route for {self.truck.driver_name} - {self.created_at.strftime('%Y-%m-%d')}"
    
    class Meta:
        ordering = ['-created_at']


class AlertNotification(models.Model):
    """
    Smart alert system for critical events
    """
    ALERT_TYPE_CHOICES = [
        ('WASTE_BIN_FULL', 'Waste Bin Full'),
        ('TEMPERATURE_CRITICAL', 'Temperature Critical'),
        ('HUMIDITY_CRITICAL', 'Humidity Critical'),
        ('DEVICE_OFFLINE', 'Device Offline'),
        ('TASK_TIMEOUT', 'Task Timeout'),
        ('FUEL_LOW', 'Fuel Low'),
        ('MAINTENANCE_DUE', 'Maintenance Due'),
        ('ENERGY_SPIKE', 'Energy Spike'),
    ]
    CHANNEL_CHOICES = [
        ('APP', 'In-App'),
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
        ('TELEGRAM', 'Telegram'),
        ('PUSH', 'Push Notification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('CRITICAL', 'Critical')], default='INFO')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='APP')
    recipient = models.CharField(max_length=255, help_text="Phone number, email, or user ID")
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    related_waste_bin = models.ForeignKey(WasteBin, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    related_facility = models.ForeignKey(Facility, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    related_truck = models.ForeignKey(Truck, on_delete=models.CASCADE, null=True, blank=True, related_name='alerts')
    
    def __str__(self):
        return f"{self.alert_type} - {self.severity} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-created_at']


class ClimateSchedule(models.Model):
    """
    Automated climate control schedules for facilities
    """
    DAY_CHOICES = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    ]
    ACTION_CHOICES = [
        ('INCREASE_TEMP', 'Increase Temperature'),
        ('DECREASE_TEMP', 'Decrease Temperature'),
        ('MAINTAIN_TEMP', 'Maintain Temperature'),
        ('INCREASE_HUMIDITY', 'Increase Humidity'),
        ('DECREASE_HUMIDITY', 'Decrease Humidity'),
        ('SHUTDOWN', 'Shutdown'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='schedules')
    boiler = models.ForeignKey(Boiler, on_delete=models.CASCADE, null=True, blank=True, related_name='schedules')
    name = models.CharField(max_length=255, help_text="Schedule name")
    days_of_week = models.JSONField(help_text="List of active days ['MON', 'TUE', ...]")
    start_time = models.TimeField()
    end_time = models.TimeField()
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    target_temperature = models.FloatField(null=True, blank=True)
    target_humidity = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.facility.name}"
    
    class Meta:
        ordering = ['start_time']


class EnergyReport(models.Model):
    """
    Energy consumption and cost analysis reports
    """
    REPORT_TYPE_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='energy_reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_energy_kwh = models.FloatField(help_text="Total energy consumed in kWh")
    total_cost = models.FloatField(help_text="Total cost in local currency")
    average_temperature = models.FloatField()
    average_humidity = models.FloatField()
    efficiency_score = models.FloatField(help_text="0-100 score")
    cost_savings = models.FloatField(default=0, help_text="Savings compared to previous period")
    recommendations = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.CharField(max_length=100, default='SYSTEM')
    
    def __str__(self):
        return f"{self.facility.name} - {self.report_type} - {self.start_date}"
    
    class Meta:
        ordering = ['-generated_at']


class WastePrediction(models.Model):
    """
    AI-based predictions for waste bin fill levels
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    waste_bin = models.ForeignKey(WasteBin, on_delete=models.CASCADE, related_name='predictions')
    prediction_date = models.DateField()
    predicted_fill_level = models.IntegerField(help_text="Predicted fill level 0-100")
    confidence = models.FloatField(help_text="Prediction confidence 0-100")
    will_be_full = models.BooleanField(default=False)
    recommended_collection_date = models.DateField(null=True, blank=True)
    based_on_data_points = models.IntegerField(help_text="Number of historical data points used")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Prediction for {self.waste_bin.address} on {self.prediction_date}"
    
    class Meta:
        ordering = ['-prediction_date']


class MaintenanceSchedule(models.Model):
    """
    Maintenance schedule for facilities and equipment
    """
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('OVERDUE', 'Overdue'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='maintenance_schedules')
    boiler = models.ForeignKey(Boiler, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_schedules')
    scheduled_date = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    task_description = models.TextField()
    assigned_technician = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    estimated_cost = models.FloatField(null=True, blank=True)
    actual_cost = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Maintenance: {self.facility.name} - {self.scheduled_date}"
    
    class Meta:
        ordering = ['scheduled_date']


class DriverPerformance(models.Model):
    """
    Track driver performance metrics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='performance_records')
    date = models.DateField()
    bins_collected = models.IntegerField(default=0)
    total_distance = models.FloatField(default=0, help_text="km")
    total_time = models.IntegerField(default=0, help_text="minutes")
    fuel_used = models.FloatField(default=0, help_text="liters")
    tasks_completed = models.IntegerField(default=0)
    tasks_rejected = models.IntegerField(default=0)
    average_response_time = models.IntegerField(default=0, help_text="Average time to accept task in seconds")
    rating = models.FloatField(default=5.0, help_text="Performance rating 1-5")
    
    def __str__(self):
        return f"{self.truck.driver_name} - {self.date}"
    
    class Meta:
        ordering = ['-date']
        unique_together = ['truck', 'date']