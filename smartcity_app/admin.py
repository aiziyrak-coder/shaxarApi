from django.contrib import admin
from django.contrib.admin import widgets
from .models import (
    User, Coordinate, Region, District, Organization, WasteBin, Truck,
    MoistureSensor, Room, Boiler, Facility, AirSensor, SOSColumn,
    EcoViolation, ConstructionMission, ConstructionSite, LightROI,
    LightPole, Bus, ResponsibleOrg, CallRequest, CallRequestTimeline,
    Notification, ReportEntry, UtilityNode, DeviceHealth, IoTDevice,
    WasteTask, RouteOptimization, AlertNotification, ClimateSchedule,
    EnergyReport, WastePrediction, MaintenanceSchedule, DriverPerformance
)

# Import Room separately to avoid admin issues
from .models import Room

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_filter = ['is_staff', 'is_superuser', 'date_joined']


@admin.register(Coordinate)
class CoordinateAdmin(admin.ModelAdmin):
    list_display = ['id', 'lat', 'lng']
    list_filter = ['lat', 'lng']
    search_fields = ['id']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'center']
    list_filter = ['name']
    search_fields = ['name', 'id']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'region', 'center']
    list_filter = ['region', 'name']
    search_fields = ['name', 'id']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'login', 'region', 'district']
    list_filter = ['type', 'region', 'district']
    search_fields = ['name', 'login', 'type']
    readonly_fields = ['id']


@admin.register(WasteBin)
class WasteBinAdmin(admin.ModelAdmin):
    list_display = ['id', 'organization', 'address', 'fill_level', 'is_full']
    list_filter = ['organization', 'is_full', 'fill_level']
    search_fields = ['address', 'id']

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ['id', 'organization', 'driver_name', 'plate_number', 'status']
    list_filter = ['organization', 'status']
    search_fields = ['driver_name', 'plate_number', 'id']


@admin.register(MoistureSensor)
class MoistureSensorAdmin(admin.ModelAdmin):
    list_display = ['id', 'mfy', 'status', 'moisture_level']
    list_filter = ['status', 'mfy']
    search_fields = ['mfy', 'id']


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'overall_status']
    list_filter = ['type', 'overall_status']
    search_fields = ['name', 'id']


@admin.register(AirSensor)
class AirSensorAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'mfy', 'aqi', 'status']
    list_filter = ['status', 'mfy']
    search_fields = ['name', 'mfy', 'id']


@admin.register(SOSColumn)
class SOSColumnAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'mfy', 'status']
    list_filter = ['status', 'mfy']
    search_fields = ['name', 'mfy', 'id']


@admin.register(EcoViolation)
class EcoViolationAdmin(admin.ModelAdmin):
    list_display = ['id', 'location_name', 'mfy', 'timestamp', 'confidence']
    list_filter = ['mfy', 'timestamp']
    search_fields = ['location_name', 'mfy', 'id']


@admin.register(ConstructionSite)
class ConstructionSiteAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'status', 'overall_progress']
    list_filter = ['status']
    search_fields = ['name', 'id']


@admin.register(LightPole)
class LightPoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'address', 'status', 'luminance']
    list_filter = ['status']
    search_fields = ['address', 'id']


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ['id', 'route_number', 'plate_number', 'driver_name', 'status']
    list_filter = ['status', 'route_number']
    search_fields = ['route_number', 'plate_number', 'driver_name', 'id']


@admin.register(CallRequest)
class CallRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'citizen_name', 'category', 'status', 'timestamp']
    list_filter = ['status', 'category', 'timestamp']
    search_fields = ['citizen_name', 'category', 'id']


@admin.register(DeviceHealth)
class DeviceHealthAdmin(admin.ModelAdmin):
    list_display = ['id', 'battery_level', 'signal_strength', 'is_online']
    list_filter = ['is_online']
    search_fields = ['id']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'facility', 'target_humidity', 'humidity', 'status')
    list_filter = ('status', 'name', 'facility')
    search_fields = ('name', 'id', 'facility__name')
    
    # Explicitly define fields to make id editable
    fields = ('id', 'name', 'facility', 'floor', 'capacity', 'is_occupied', 
              'target_humidity', 'humidity', 'temperature', 'status', 'trend', 
              'created_at', 'last_updated')
    
    def get_readonly_fields(self, request, obj=None):
        """Override to exclude id from readonly fields"""
        # Only timestamps are readonly, id is editable
        return ('created_at', 'last_updated')
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Override to make id field editable"""
        # Make id field editable
        if db_field.name == 'id':
            kwargs['widget'] = widgets.AdminTextInputWidget(attrs={'class': 'vTextField'})
            kwargs['required'] = True
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    def get_form(self, request, obj=None, **kwargs):
        """Override to ensure id field is editable in admin form"""
        # Get the form class
        form = super().get_form(request, obj, **kwargs)
        
        # Make id field editable by removing any readonly/disabled attributes
        if 'id' in form.base_fields:
            id_field = form.base_fields['id']
            # Remove readonly/disabled attributes
            id_field.disabled = False
            id_field.widget.attrs.pop('readonly', None)
            id_field.widget.attrs.pop('disabled', None)
            
            # For new objects, make id required
            if obj is None:
                id_field.required = True
        
        return form
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # Simple override to avoid context copying issues
        return super().changeform_view(request, object_id, form_url, extra_context)
    
    def changelist_view(self, request, extra_context=None):
        # Simple override to avoid context copying issues
        return super().changelist_view(request, extra_context)


@admin.register(Boiler)
class BoilerAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'status', 'humidity', 'temperature', 'created_at', 'last_updated']
    list_filter = ['status']
    search_fields = ['name', 'id']


@admin.register(ConstructionMission)
class ConstructionMissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'stage_name', 'stage_type', 'status', 'progress', 'deadline']
    list_filter = ['stage_type', 'status']
    search_fields = ['stage_name', 'id']


@admin.register(LightROI)
class LightROIAdmin(admin.ModelAdmin):
    list_display = ['id', 'label', 'x', 'y', 'width', 'height']
    search_fields = ['label', 'id']


@admin.register(ResponsibleOrg)
class ResponsibleOrgAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'active_brigades', 'total_brigades', 'current_load', 'contact_phone']
    list_filter = ['type']
    search_fields = ['name', 'type', 'id']


@admin.register(CallRequestTimeline)
class CallRequestTimelineAdmin(admin.ModelAdmin):
    list_display = ['id', 'call_request', 'step', 'actor', 'status', 'timestamp']
    list_filter = ['status', 'actor']
    search_fields = ['step', 'actor', 'id', 'call_request__id']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'type', 'read', 'timestamp']
    list_filter = ['type', 'read', 'timestamp']
    search_fields = ['title', 'user__username', 'id']


@admin.register(ReportEntry)
class ReportEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'timestamp', 'location_name', 'category', 'metric_label', 'value', 'status', 'responsible']
    list_filter = ['category', 'status', 'timestamp']
    search_fields = ['location_name', 'metric_label', 'id']


@admin.register(UtilityNode)
class UtilityNodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'mfy', 'status', 'load', 'capacity', 'active_tickets']
    list_filter = ['type', 'status', 'mfy']
    search_fields = ['name', 'mfy', 'id']


@admin.register(IoTDevice)
class IoTDeviceAdmin(admin.ModelAdmin):
    list_display = ['id', 'device_id', 'device_type', 'is_active', 'last_seen', 'room', 'boiler', 'current_temperature', 'current_humidity']
    list_filter = ['device_type', 'is_active']
    search_fields = ['device_id', 'id']


# ==================== NEW ADMIN INTERFACES ====================

@admin.register(WasteTask)
class WasteTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'waste_bin', 'assigned_truck', 'status', 'priority', 'created_at', 'completed_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['id', 'waste_bin__address', 'assigned_truck__driver_name']
    readonly_fields = ['created_at']


@admin.register(RouteOptimization)
class RouteOptimizationAdmin(admin.ModelAdmin):
    list_display = ['id', 'truck', 'total_distance', 'estimated_time', 'fuel_estimate', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['id', 'truck__driver_name']
    readonly_fields = ['created_at']


@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'alert_type', 'severity', 'channel', 'recipient', 'is_sent', 'created_at']
    list_filter = ['alert_type', 'severity', 'channel', 'is_sent', 'created_at']
    search_fields = ['title', 'message', 'recipient']
    readonly_fields = ['created_at', 'sent_at']


@admin.register(ClimateSchedule)
class ClimateScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'facility', 'start_time', 'end_time', 'action', 'is_active']
    list_filter = ['action', 'is_active', 'facility']
    search_fields = ['name', 'facility__name']


@admin.register(EnergyReport)
class EnergyReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'facility', 'report_type', 'start_date', 'end_date', 'total_energy_kwh', 'total_cost', 'efficiency_score']
    list_filter = ['report_type', 'generated_at', 'facility']
    search_fields = ['facility__name']
    readonly_fields = ['generated_at']


@admin.register(WastePrediction)
class WastePredictionAdmin(admin.ModelAdmin):
    list_display = ['id', 'waste_bin', 'prediction_date', 'predicted_fill_level', 'confidence', 'will_be_full']
    list_filter = ['will_be_full', 'prediction_date', 'created_at']
    search_fields = ['waste_bin__address']
    readonly_fields = ['created_at']


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'facility', 'boiler', 'scheduled_date', 'status', 'assigned_technician']
    list_filter = ['status', 'scheduled_date', 'facility']
    search_fields = ['facility__name', 'assigned_technician', 'task_description']


@admin.register(DriverPerformance)
class DriverPerformanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'truck', 'date', 'bins_collected', 'total_distance', 'rating']
    list_filter = ['date', 'truck']
    search_fields = ['truck__driver_name']