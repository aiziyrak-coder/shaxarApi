from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
import logging
from django.conf import settings

# Configure logging for this module
logger = logging.getLogger(__name__)
from .models import (
    Organization, WasteBin, Truck, MoistureSensor, Facility, AirSensor, 
    SOSColumn, EcoViolation, ConstructionSite, LightPole, Bus, CallRequest,
    Coordinate, Region, District, Room, Boiler, ConstructionMission, LightROI,
    ResponsibleOrg, CallRequestTimeline, Notification, ReportEntry, UtilityNode,
    DeviceHealth, IoTDevice, WasteTask, RouteOptimization, AlertNotification,
    ClimateSchedule, EnergyReport, WastePrediction, MaintenanceSchedule, DriverPerformance
)
from .serializers import (
    OrganizationSerializer, WasteBinSerializer, TruckSerializer, 
    MoistureSensorSerializer, FacilitySerializer, AirSensorSerializer, 
    SOSColumnSerializer, EcoViolationSerializer, ConstructionSiteSerializer, 
    LightPoleSerializer, BusSerializer, CallRequestSerializer, 
    RegionSerializer, DistrictSerializer, RoomSerializer, BoilerSerializer,
    ConstructionMissionSerializer, LightROISerializer, ResponsibleOrgSerializer,
    CallRequestTimelineSerializer, NotificationSerializer, ReportEntrySerializer,
    UtilityNodeSerializer, DeviceHealthSerializer, IoTDeviceSerializer,
    WasteTaskSerializer, RouteOptimizationSerializer, AlertNotificationSerializer,
    ClimateScheduleSerializer, EnergyReportSerializer, WastePredictionSerializer,
    MaintenanceScheduleSerializer, DriverPerformanceSerializer
)
import json
import uuid
import requests

# Authentication Views
@csrf_exempt
@api_view(['POST'])
@permission_classes([])  # Allow unauthenticated users to log in
def login_view(request):
    """
    Handle user authentication for different roles
    """
    try:
        data = json.loads(request.body)
        login_param = data.get('login')
        password = data.get('password')
        
        # First, try to find the user as an organization
        try:
            org = Organization.objects.get(login=login_param)
            if org.password == password:  # In production, use Django's password hashing
                # Create a user session for the organization
                user, created = User.objects.get_or_create(username=org.login)
                login(request, user)
                
                # Create or get authentication token
                token, created = Token.objects.get_or_create(user=user)
                
                # Add organization to user for context
                request.session['organization_id'] = str(org.id)
                
                return Response({
                    'success': True,
                    'token': token.key,
                    'user': {
                        'id': str(org.id),
                        'name': org.name,
                        'role': 'ORGANIZATION',
                        'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE']  # Only WASTE and CLIMATE for Farg'ona
                    }
                })
        except Organization.DoesNotExist:
            pass
        try:
            truck = Truck.objects.get(login=login_param)
            if truck.password == password:  # In production, use proper password hashing
                # Create a user session for the truck/driver
                user, created = User.objects.get_or_create(username=truck.login)
                login(request, user)
                
                # Create or get authentication token
                token, created = Token.objects.get_or_create(user=user)
                
                # Add truck to user for context
                request.session['truck_id'] = str(truck.id)
                
                return Response({
                    'success': True,
                    'token': token.key,
                    'user': {
                        'id': str(truck.id),
                        'name': truck.driver_name,
                        'role': 'DRIVER',
                        'enabled_modules': ['WASTE']  # Drivers typically only have waste module
                    }
                })
        except Truck.DoesNotExist:
            pass
        
        # Try superadmin credentials
        if login_param == 'superadmin' and password == '123':
            user, created = User.objects.get_or_create(username='superadmin')
            login(request, user)
            
            # Create or get authentication token
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'success': True,
                'token': token.key,
                'user': {
                    'id': 'superadmin',
                    'name': 'Super Admin',
                    'role': 'SUPERADMIN',
                    'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE']  # Only WASTE and CLIMATE for Farg'ona
                }
            })
        
        # Try authenticating with Django's built-in User model (for admin users)
        django_user = authenticate(username=login_param, password=password)
        if django_user is not None:
            login(request, django_user)
            
            # Create or get authentication token for Django user
            token, created = Token.objects.get_or_create(user=django_user)
            
            # Determine role based on user permissions
            role = 'SUPERADMIN' if django_user.is_superuser else 'ADMIN'
            
            return Response({
                'success': True,
                'token': token.key,
                'user': {
                    'id': str(django_user.id),
                    'name': django_user.username,
                    'role': role,
                    'enabled_modules': ['DASHBOARD', 'WASTE', 'CLIMATE']  # Only WASTE and CLIMATE for Farg'ona
                }
            })
        
        return Response({
            'success': False,
            'message': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
        
    except json.JSONDecodeError:
        return Response({
            'success': False,
            'message': 'Invalid JSON'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([])  # Allow unauthenticated users to validate tokens
def validate_token(request):
    """
    Validate if the token is still valid
    Supports both GET (with Authorization header) and POST (with token in body)
    """
    # Try to get token from Authorization header first
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    token = None
    
    if auth_header.startswith('Token '):
        token_key = auth_header.split('Token ')[1]
        try:
            from rest_framework.authtoken.models import Token
            token_obj = Token.objects.get(key=token_key)
            user = token_obj.user
            # User is authenticated via token
            response_data = {'valid': True, 'user_id': str(user.id), 'username': user.username}
            
            # Include organization ID if it exists in session
            org_id = request.session.get('organization_id')
            if org_id:
                response_data['organization_id'] = org_id
            
            return Response(response_data)
        except Token.DoesNotExist:
            return Response({'valid': False, 'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Fallback: Check if user is authenticated via session
    if request.user.is_authenticated:
        response_data = {'valid': True}
        org_id = request.session.get('organization_id')
        if org_id:
            response_data['organization_id'] = org_id
        return Response(response_data)
    else:
        return Response({'valid': False, 'error': 'No valid authentication'}, status=status.HTTP_401_UNAUTHORIZED)


# Class-based views for all models
class WasteBinListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only bins belonging to their organization
            bins = WasteBin.objects.filter(organization_id=org_id).select_related('location', 'organization').distinct()
        else:
            # For superadmin, return all bins
            bins = WasteBin.objects.all().select_related('location', 'organization').distinct()
        
        # CRITICAL: Remove duplicates by ID to prevent frontend showing duplicates
        # This ensures that even if database has duplicates, API returns unique bins
        unique_bins = {}
        for bin in bins:
            if bin.id not in unique_bins:
                unique_bins[bin.id] = bin
        
        # Convert back to list
        unique_bins_list = list(unique_bins.values())
        
        # Log if duplicates were found
        if len(bins) != len(unique_bins_list):
            logger.warning(f"⚠️ Duplicate bins detected in database: {len(bins)} total, {len(unique_bins_list)} unique. Removed {len(bins) - len(unique_bins_list)} duplicates.")
        
        serializer = WasteBinSerializer(unique_bins_list, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        # 1. 'data'ni har doim requestdan nusxalab olamiz (IF dan tashqarida)
        data = request.data.copy()
        
        # 2. Org_id bo'lsa, uni ma'lumotlarga qo'shamiz
        org_id = request.session.get('organization_id')
        if org_id:
            data['organization'] = org_id
        
        # CRITICAL: Check for duplicate bins by address or location before creating
        address = data.get('address')
        location_data = data.get('location')
        
        if address and location_data:
            lat = location_data.get('lat')
            lng = location_data.get('lng')
            
            # Check for existing bin with same address
            existing_by_address = WasteBin.objects.filter(address=address, organization_id=org_id).first()
            if existing_by_address:
                logger.warning(f"⚠️ Duplicate bin detected by address: {address}. Returning existing bin.")
                serializer = WasteBinSerializer(existing_by_address, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            # Check for existing bin with same location (within 0.0001 degrees ~11 meters)
            if lat and lng:
                from django.db.models import Q
                existing_by_location = WasteBin.objects.filter(
                    Q(location__lat__gte=lat-0.0001) & Q(location__lat__lte=lat+0.0001) &
                    Q(location__lng__gte=lng-0.0001) & Q(location__lng__lte=lng+0.0001),
                    organization_id=org_id
                ).first()
                if existing_by_location:
                    logger.warning(f"⚠️ Duplicate bin detected by location: ({lat}, {lng}). Returning existing bin.")
                    serializer = WasteBinSerializer(existing_by_location, context={'request': request})
                    return Response(serializer.data, status=status.HTTP_200_OK)
            
        # Endi 'data' har qanday holatda ham mavjud
        serializer = WasteBinSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            # Use database transaction to ensure data consistency
            from django.db import transaction
            
            try:
                with transaction.atomic():
                    waste_bin = serializer.save()
                    
                    # AUTO-GENERATE QR CODE
                    try:
                        import qrcode
                        import os
                        from django.conf import settings
                        
                        # Create QR codes directory
                        qr_codes_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
                        os.makedirs(qr_codes_dir, exist_ok=True)
                        
                        # QR code data - Telegram bot link with bin ID
                        qr_data = f"https://t.me/tozafargonabot?start={waste_bin.id}"
                        
                        # Generate QR code
                        qr = qrcode.QRCode(version=1, box_size=10, border=5)
                        qr.add_data(qr_data)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        
                        # Save QR code
                        qr_filename = f"bin_{waste_bin.id}_qr.png"
                        qr_path = os.path.join(qr_codes_dir, qr_filename)
                        img.save(qr_path)
                        
                        # Update bin with QR code URL (always use production domain)
                        waste_bin.qr_code_url = f"https://ferganaapi.cdcgroup.uz/media/qr_codes/{qr_filename}"
                        waste_bin.save()
                        
                        logger.info(f"✅ QR code yaratildi: {waste_bin.qr_code_url}")
                    except Exception as e:
                        logger.error(f"⚠️ QR code yaratishda xato: {e}")
                        # Don't fail the whole request if QR code generation fails
                    
                    # Return updated data with QR code
                    serializer = WasteBinSerializer(waste_bin, context={'request': request})
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"❌ Error creating waste bin: {str(e)}", exc_info=True)
                return Response({
                    'error': 'Failed to create waste bin',
                    'detail': str(e) if settings.DEBUG else 'Internal server error'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Xatolik bo'lsa nima xatoligini ko'rsatish
        logger.warning(f"⚠️ WasteBin serializer validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Exempt CSRF for API views that use token authentication
@method_decorator(csrf_exempt, name='dispatch')
class WasteBinDetailView(APIView):
    def get(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = WasteBinSerializer(bin)
        return Response(serializer.data)
    
    def put(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = WasteBinSerializer(bin, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Use partial=True to allow partial updates
        serializer = WasteBinSerializer(bin, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        bin.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name='dispatch')
class WasteBinImageUpdateView(APIView):
    def patch(self, request, pk):
        """Update only the image_url, is_full, fill_level, image_source, and last_analysis fields for a waste bin"""
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Only allow updating specific fields
        allowed_fields = ['image_url', 'is_full', 'fill_level', 'image_source', 'last_analysis', 'image']
        update_data = {}
        
        for field in allowed_fields:
            if field in request.data:
                update_data[field] = request.data[field]
        
        # Set default image_source if not provided
        if 'image_source' not in update_data:
            update_data['image_source'] = 'BOT'
        
        # Set default last_analysis if not provided
        if 'last_analysis' not in update_data:
            update_data['last_analysis'] = 'Bot orqali yangilandi'
        
        # Update only the allowed fields
        for field, value in update_data.items():
            if field == 'image' and value:
                # Handle file upload
                setattr(bin, field, value)
            else:
                setattr(bin, field, value)
        
        bin.save()
        
        # Return the updated bin
        serializer = WasteBinSerializer(bin)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class WasteBinImageFileUpdateView(APIView):
    def patch(self, request, pk):
        """Update the image field with an uploaded file for a waste bin"""
        bin = get_object_or_404(WasteBin, pk=pk)
        
        # Check if user has permission to access this bin
        org_id = request.session.get('organization_id')
        if org_id and str(bin.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Handle file upload
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            bin.image = image_file
            
            # Optionally update other fields from request data
            if 'is_full' in request.data:
                bin.is_full = request.data['is_full']
            if 'fill_level' in request.data:
                bin.fill_level = request.data['fill_level']
            if 'image_source' in request.data:
                bin.image_source = request.data['image_source']
            if 'last_analysis' in request.data:
                bin.last_analysis = request.data['last_analysis']
            
            bin.save()
            
            serializer = WasteBinSerializer(bin)
            return Response(serializer.data)
        else:
            return Response({'error': 'No image file provided'}, status=status.HTTP_400_BAD_REQUEST)


class TruckListCreateView(APIView):
    def get(self, request):
        # Get the user's organization if available
        org_id = request.session.get('organization_id')
        
        if org_id:
            # For organization users, return only trucks belonging to their organization
            trucks = Truck.objects.filter(organization_id=org_id).distinct()
        else:
            # For superadmin, return all trucks
            trucks = Truck.objects.all().distinct()
        
        # Remove duplicates by ID
        unique_trucks = {}
        for truck in trucks:
            if truck.id not in unique_trucks:
                unique_trucks[truck.id] = truck
        
        unique_trucks_list = list(unique_trucks.values())
        
        serializer = TruckSerializer(unique_trucks_list, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = TruckSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TruckDetailView(APIView):
    def get(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        
        # Check if user has permission to access this truck
        org_id = request.session.get('organization_id')
        if org_id and str(truck.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TruckSerializer(truck)
        return Response(serializer.data)
    
    def put(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        
        # Check if user has permission to access this truck
        org_id = request.session.get('organization_id')
        if org_id and str(truck.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TruckSerializer(truck, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        
        # Check if user has permission to access this truck
        org_id = request.session.get('organization_id')
        if org_id and str(truck.organization_id) != org_id:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        truck.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegionListCreateView(APIView):
    def get(self, request):
        regions = Region.objects.all()
        serializer = RegionSerializer(regions, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = RegionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegionDetailView(APIView):
    def get(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        serializer = RegionSerializer(region)
        return Response(serializer.data)
    
    def put(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        serializer = RegionSerializer(region, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        region = get_object_or_404(Region, pk=pk)
        region.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DistrictListCreateView(APIView):
    def get(self, request):
        districts = District.objects.all()
        serializer = DistrictSerializer(districts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = DistrictSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DistrictDetailView(APIView):
    def get(self, request, pk):
        district = get_object_or_404(District, pk=pk)
        serializer = DistrictSerializer(district)
        return Response(serializer.data)
    
    def put(self, request, pk):
        district = get_object_or_404(District, pk=pk)
        serializer = DistrictSerializer(district, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        district = get_object_or_404(District, pk=pk)
        district.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationListCreateView(APIView):
    def get(self, request):
        organizations = Organization.objects.all()
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationDetailView(APIView):
    def get(self, request, pk):
        # Try to get by ID first, then by login as fallback
        try:
            # Check if pk is a valid UUID
            uuid_obj = uuid.UUID(pk)
            organization = get_object_or_404(Organization, pk=pk)
        except ValueError:
            # If not a UUID, try to get by login
            organization = get_object_or_404(Organization, login=pk)
        
        serializer = OrganizationSerializer(organization)
        return Response(serializer.data)
    
    def put(self, request, pk):
        # Try to get by ID first, then by login as fallback
        try:
            # Check if pk is a valid UUID
            uuid_obj = uuid.UUID(pk)
            organization = get_object_or_404(Organization, pk=pk)
        except ValueError:
            # If not a UUID, try to get by login
            try:
                organization = Organization.objects.get(login=pk)
            except Organization.DoesNotExist:
                # If the organization doesn't exist, create a new one with the given pk as login
                # Process the data to handle region/district references properly
                data = request.data.copy()
                data['login'] = pk  # Use the pk from URL as login
                
                # Handle region and district lookups if they're provided as names
                if 'regionId' in data and data['regionId']:
                    try:
                        # First try to get by UUID
                        region = Region.objects.get(id=data['regionId'])
                        data['region'] = region.pk
                    except Region.DoesNotExist:
                        try:
                            # If UUID lookup fails, try to get by name
                            region = Region.objects.get(name=data['regionId'])
                            data['region'] = region.pk
                        except Region.DoesNotExist:
                            return Response({'error': 'Region not found'}, status=status.HTTP_400_BAD_REQUEST)
                    # Remove the regionId field since we're using region now
                    del data['regionId']
                
                if 'districtId' in data and data['districtId']:
                    try:
                        # First try to get by UUID
                        district = District.objects.get(id=data['districtId'])
                        data['district'] = district.pk
                    except District.DoesNotExist:
                        try:
                            # If UUID lookup fails, try to get by name
                            district = District.objects.get(name=data['districtId'])
                            data['district'] = district.pk
                        except District.DoesNotExist:
                            return Response({'error': 'District not found'}, status=status.HTTP_400_BAD_REQUEST)
                    # Remove the districtId field since we're using district now
                    del data['districtId']
                
                # Create the organization with properly processed data
                serializer = OrganizationSerializer(data=data)
                if serializer.is_valid():
                    organization = serializer.save()
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # For updating existing organization
        # Process the data to handle region/district references properly
        data = request.data.copy()
        
        # Handle region and district lookups if they're provided as names
        if 'regionId' in data and data['regionId']:
            try:
                # First try to get by UUID
                region = Region.objects.get(id=data['regionId'])
                data['region'] = region.pk
            except Region.DoesNotExist:
                try:
                    # If UUID lookup fails, try to get by name
                    region = Region.objects.get(name=data['regionId'])
                    data['region'] = region.pk
                except Region.DoesNotExist:
                    return Response({'error': 'Region not found'}, status=status.HTTP_400_BAD_REQUEST)
            # Remove the regionId field since we're using region now
            del data['regionId']
        
        if 'districtId' in data and data['districtId']:
            try:
                # First try to get by UUID
                district = District.objects.get(id=data['districtId'])
                data['district'] = district.pk
            except District.DoesNotExist:
                try:
                    # If UUID lookup fails, try to get by name
                    district = District.objects.get(name=data['districtId'])
                    data['district'] = district.pk
                except District.DoesNotExist:
                    return Response({'error': 'District not found'}, status=status.HTTP_400_BAD_REQUEST)
            # Remove the districtId field since we're using district now
            del data['districtId']
        
        serializer = OrganizationSerializer(organization, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        # Try to get by ID first, then by login as fallback
        try:
            # Check if pk is a valid UUID
            uuid_obj = uuid.UUID(pk)
            organization = get_object_or_404(Organization, pk=pk)
        except ValueError:
            # If not a UUID, try to get by login
            organization = get_object_or_404(Organization, login=pk)
        
        organization.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MoistureSensorListCreateView(APIView):
    def get(self, request):
        sensors = MoistureSensor.objects.all()
        serializer = MoistureSensorSerializer(sensors, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = MoistureSensorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MoistureSensorDetailView(APIView):
    def get(self, request, pk):
        sensor = get_object_or_404(MoistureSensor, pk=pk)
        serializer = MoistureSensorSerializer(sensor)
        return Response(serializer.data)
    
    def put(self, request, pk):
        sensor = get_object_or_404(MoistureSensor, pk=pk)
        serializer = MoistureSensorSerializer(sensor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        sensor = get_object_or_404(MoistureSensor, pk=pk)
        sensor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoomListCreateView(APIView):
    def get(self, request):
        rooms = Room.objects.all().distinct()
        
        # Remove duplicates by ID
        unique_rooms = {}
        for room in rooms:
            if room.id not in unique_rooms:
                unique_rooms[room.id] = room
        
        unique_rooms_list = list(unique_rooms.values())
        
        serializer = RoomSerializer(unique_rooms_list, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoomDetailView(APIView):
    def get(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        serializer = RoomSerializer(room)
        return Response(serializer.data)
    
    def put(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        serializer = RoomSerializer(room, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BoilerListCreateView(APIView):
    def get(self, request):
        boilers = Boiler.objects.all().distinct()
        
        # Remove duplicates by ID
        unique_boilers = {}
        for boiler in boilers:
            if boiler.id not in unique_boilers:
                unique_boilers[boiler.id] = boiler
        
        unique_boilers_list = list(unique_boilers.values())
        
        serializer = BoilerSerializer(unique_boilers_list, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = BoilerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BoilerDetailView(APIView):
    def get(self, request, pk):
        boiler = get_object_or_404(Boiler, pk=pk)
        serializer = BoilerSerializer(boiler)
        return Response(serializer.data)
    
    def put(self, request, pk):
        boiler = get_object_or_404(Boiler, pk=pk)
        serializer = BoilerSerializer(boiler, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        boiler = get_object_or_404(Boiler, pk=pk)
        boiler.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FacilityListCreateView(APIView):
    def get(self, request):
        from django.db.models import Prefetch
        # Prefetch boilers and their connected rooms for efficient querying
        boilers_prefetch = Prefetch('boilers', Boiler.objects.prefetch_related('connected_rooms', 'device_health'))
        facilities = Facility.objects.prefetch_related(boilers_prefetch).all().distinct()
        
        # Remove duplicates by ID
        unique_facilities = {}
        for facility in facilities:
            if facility.id not in unique_facilities:
                unique_facilities[facility.id] = facility
        
        unique_facilities_list = list(unique_facilities.values())
        
        serializer = FacilitySerializer(unique_facilities_list, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = FacilitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FacilityDetailView(APIView):
    def get(self, request, pk):
        from django.db.models import Prefetch
        # Prefetch boilers and their connected rooms for efficient querying
        boilers_prefetch = Prefetch('boilers', Boiler.objects.prefetch_related('connected_rooms', 'device_health'))
        facility = get_object_or_404(Facility.objects.prefetch_related(boilers_prefetch), pk=pk)
        serializer = FacilitySerializer(facility)
        return Response(serializer.data)
    
    def put(self, request, pk):
        facility = get_object_or_404(Facility, pk=pk)
        serializer = FacilitySerializer(facility, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        facility = get_object_or_404(Facility, pk=pk)
        facility.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AirSensorListCreateView(APIView):
    def get(self, request):
        # AirSensor model doesn't have organization field, so return all sensors
        # In the future, if organization support is needed, add organization ForeignKey to the model
        sensors = AirSensor.objects.all()
        
        serializer = AirSensorSerializer(sensors, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = AirSensorSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AirSensorDetailView(APIView):
    def get(self, request, pk):
        sensor = get_object_or_404(AirSensor, pk=pk)
        serializer = AirSensorSerializer(sensor)
        return Response(serializer.data)
    
    def put(self, request, pk):
        sensor = get_object_or_404(AirSensor, pk=pk)
        serializer = AirSensorSerializer(sensor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        sensor = get_object_or_404(AirSensor, pk=pk)
        sensor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SOSColumnListCreateView(APIView):
    def get(self, request):
        # SOSColumn model doesn't have organization field, so return all columns
        # In the future, if organization support is needed, add organization ForeignKey to the model
        columns = SOSColumn.objects.all()
        
        serializer = SOSColumnSerializer(columns, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = SOSColumnSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SOSColumnDetailView(APIView):
    def get(self, request, pk):
        column = get_object_or_404(SOSColumn, pk=pk)
        serializer = SOSColumnSerializer(column)
        return Response(serializer.data)
    
    def put(self, request, pk):
        column = get_object_or_404(SOSColumn, pk=pk)
        serializer = SOSColumnSerializer(column, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        column = get_object_or_404(SOSColumn, pk=pk)
        column.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EcoViolationListCreateView(APIView):
    def get(self, request):
        # EcoViolation model doesn't have organization field, so return all violations
        # In the future, if organization support is needed, add organization ForeignKey to the model
        violations = EcoViolation.objects.all()
        
        serializer = EcoViolationSerializer(violations, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = EcoViolationSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EcoViolationDetailView(APIView):
    def get(self, request, pk):
        violation = get_object_or_404(EcoViolation, pk=pk)
        serializer = EcoViolationSerializer(violation)
        return Response(serializer.data)
    
    def put(self, request, pk):
        violation = get_object_or_404(EcoViolation, pk=pk)
        serializer = EcoViolationSerializer(violation, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        violation = get_object_or_404(EcoViolation, pk=pk)
        violation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConstructionSiteListCreateView(APIView):
    def get(self, request):
        # ConstructionSite model doesn't have organization field, so return all sites
        # In the future, if organization support is needed, add organization ForeignKey to the model
        sites = ConstructionSite.objects.all()
        
        serializer = ConstructionSiteSerializer(sites, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = ConstructionSiteSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConstructionSiteDetailView(APIView):
    def get(self, request, pk):
        site = get_object_or_404(ConstructionSite, pk=pk)
        serializer = ConstructionSiteSerializer(site)
        return Response(serializer.data)
    
    def put(self, request, pk):
        site = get_object_or_404(ConstructionSite, pk=pk)
        serializer = ConstructionSiteSerializer(site, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        site = get_object_or_404(ConstructionSite, pk=pk)
        site.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LightPoleListCreateView(APIView):
    def get(self, request):
        # LightPole model doesn't have organization field, so return all poles
        # In the future, if organization support is needed, add organization ForeignKey to the model
        poles = LightPole.objects.all()
        
        serializer = LightPoleSerializer(poles, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = LightPoleSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LightPoleDetailView(APIView):
    def get(self, request, pk):
        pole = get_object_or_404(LightPole, pk=pk)
        serializer = LightPoleSerializer(pole)
        return Response(serializer.data)
    
    def put(self, request, pk):
        pole = get_object_or_404(LightPole, pk=pk)
        serializer = LightPoleSerializer(pole, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        pole = get_object_or_404(LightPole, pk=pk)
        pole.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BusListCreateView(APIView):
    def get(self, request):
        # Bus model doesn't have organization field, so return all buses
        # In the future, if organization support is needed, add organization ForeignKey to the model
        buses = Bus.objects.all()
        
        serializer = BusSerializer(buses, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = BusSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BusDetailView(APIView):
    def get(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        serializer = BusSerializer(bus)
        return Response(serializer.data)
    
    def put(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        serializer = BusSerializer(bus, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        bus.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CallRequestListCreateView(APIView):
    def get(self, request):
        requests = CallRequest.objects.all()
        serializer = CallRequestSerializer(requests, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = CallRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CallRequestDetailView(APIView):
    def get(self, request, pk):
        request_obj = get_object_or_404(CallRequest, pk=pk)
        serializer = CallRequestSerializer(request_obj)
        return Response(serializer.data)
    
    def put(self, request, pk):
        request_obj = get_object_or_404(CallRequest, pk=pk)
        serializer = CallRequestSerializer(request_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        request_obj = get_object_or_404(CallRequest, pk=pk)
        request_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Add other class-based views as needed...

# Additional functional views
@api_view(['GET'])
def get_waste_bins_by_hudud(request, toza_hudud):
    """
    Get waste bins by toza hudud
    """
    bins = WasteBin.objects.filter(toza_hudud=toza_hudud)
    serializer = WasteBinSerializer(bins, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_trucks_by_hudud(request, toza_hudud):
    """
    Get trucks by toza hudud
    """
    trucks = Truck.objects.filter(toza_hudud=toza_hudud)
    serializer = TruckSerializer(trucks, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_region_districts(request, region_id):
    """
    Get districts for a specific region
    """
    districts = District.objects.filter(region_id=region_id)
    serializer = DistrictSerializer(districts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_facilities_by_type(request, facility_type):
    """
    Get facilities by type
    """
    facilities = Facility.objects.filter(type=facility_type)
    serializer = FacilitySerializer(facilities, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_air_sensors_by_status(request, status):
    """
    Get air sensors by status
    """
    sensors = AirSensor.objects.filter(status=status)
    serializer = AirSensorSerializer(sensors, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_sos_columns_by_status(request, status):
    """
    Get SOS columns by status
    """
    columns = SOSColumn.objects.filter(status=status)
    serializer = SOSColumnSerializer(columns, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_eco_violations_by_date_range(request):
    """
    Get eco violations by date range
    """
    from django.utils.dateparse import parse_date
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    violations = EcoViolation.objects.all()
    if start_date:
        start_date = parse_date(start_date)
        violations = violations.filter(timestamp__gte=start_date)
    if end_date:
        end_date = parse_date(end_date)
        violations = violations.filter(timestamp__lte=end_date)
    
    serializer = EcoViolationSerializer(violations, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_construction_sites_by_status(request, status):
    """
    Get construction sites by status
    """
    sites = ConstructionSite.objects.filter(status=status)
    serializer = ConstructionSiteSerializer(sites, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_buses_by_status(request, status):
    """
    Get buses by status
    """
    buses = Bus.objects.filter(status=status)
    serializer = BusSerializer(buses, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_call_requests_by_status(request, status):
    """
    Get call requests by status
    """
    requests = CallRequest.objects.filter(status=status)
    serializer = CallRequestSerializer(requests, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_notifications_unread(request):
    """
    Get unread notifications
    """
    notifications = Notification.objects.filter(read=False)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def mark_notification_read(request, notification_id):
    """
    Mark notification as read
    """
    notification = get_object_or_404(Notification, pk=notification_id)
    notification.read = True
    notification.save()
    serializer = NotificationSerializer(notification)
    return Response(serializer.data)


@api_view(['GET'])
def get_utility_nodes_by_type(request, utility_type):
    """
    Get utility nodes by type
    """
    nodes = UtilityNode.objects.filter(type=utility_type)
    serializer = UtilityNodeSerializer(nodes, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_utility_nodes_by_status(request, status):
    """
    Get utility nodes by status
    """
    nodes = UtilityNode.objects.filter(status=status)
    serializer = UtilityNodeSerializer(nodes, many=True)
    return Response(serializer.data)


# Search functionality
@api_view(['GET'])
def search_entities(request):
    """
    Search across all entities
    """
    query = request.GET.get('q', '')
    entity_type = request.GET.get('type', '')
    
    results = []
    
    if entity_type == 'organization' or not entity_type:
        orgs = Organization.objects.filter(name__icontains=query)
        results.extend(OrganizationSerializer(orgs, many=True).data)
    
    if entity_type == 'waste-bin' or not entity_type:
        bins = WasteBin.objects.filter(address__icontains=query)
        results.extend(WasteBinSerializer(bins, many=True).data)
    
    if entity_type == 'truck' or not entity_type:
        trucks = Truck.objects.filter(driver_name__icontains=query)
        results.extend(TruckSerializer(trucks, many=True).data)
    
    return Response({
        'query': query,
        'type': entity_type,
        'results': results
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_waste_bin_analysis(request):
    """
    API endpoint to trigger automated waste bin analysis
    """
    from smartcity_app.management.commands.analyze_waste_bins import Command
    import io
    from contextlib import redirect_stdout

    # Create a string buffer to capture output
    f = io.StringIO()
    
    # Run the analysis command
    try:
        command = Command()
        command.analyze_bins()
        return Response({
            'success': True,
            'message': 'Waste bin analysis completed successfully'
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error during analysis: {str(e)}'
        }, status=500)


# Custom views for specific functionality
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get dashboard statistics
    """
    # Get the user's organization if available
    org_id = request.session.get('organization_id')
    
    if org_id:
        # For organization users, count only their entities
        total_bins = WasteBin.objects.filter(organization_id=org_id).count()
        active_bins = WasteBin.objects.filter(organization_id=org_id, is_full=False).count()
        total_trucks = Truck.objects.filter(organization_id=org_id).count()
        busy_trucks = Truck.objects.filter(organization_id=org_id, status='BUSY').count()
    else:
        # For superadmin, count all entities
        total_bins = WasteBin.objects.count()
        active_bins = WasteBin.objects.filter(is_full=False).count()
        total_trucks = Truck.objects.count()
        busy_trucks = Truck.objects.filter(status='BUSY').count()
    
    return Response({
        'total_bins': total_bins,
        'active_bins': active_bins,
        'total_trucks': total_trucks,
        'busy_trucks': busy_trucks,
        'fill_rate': (total_bins - active_bins) / total_bins * 100 if total_bins > 0 else 0
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_organizations(request):
    """
    Get organizations for the logged-in user
    """
    org_id = request.session.get('organization_id')
    
    if org_id:
        # Return only the user's organization
        org = Organization.objects.get(id=org_id)
        serializer = OrganizationSerializer(org)
        return Response([serializer.data])
    else:
        # For superadmin, return all organizations
        organizations = Organization.objects.all()
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)


class ConstructionMissionListCreateView(APIView):
    def get(self, request):
        missions = ConstructionMission.objects.all()
        serializer = ConstructionMissionSerializer(missions, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ConstructionMissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConstructionMissionDetailView(APIView):
    def get(self, request, pk):
        mission = get_object_or_404(ConstructionMission, pk=pk)
        serializer = ConstructionMissionSerializer(mission)
        return Response(serializer.data)
    
    def put(self, request, pk):
        mission = get_object_or_404(ConstructionMission, pk=pk)
        serializer = ConstructionMissionSerializer(mission, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        mission = get_object_or_404(ConstructionMission, pk=pk)
        mission.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LightROIListCreateView(APIView):
    def get(self, request):
        rois = LightROI.objects.all()
        serializer = LightROISerializer(rois, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = LightROISerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LightROIDetailView(APIView):
    def get(self, request, pk):
        roi = get_object_or_404(LightROI, pk=pk)
        serializer = LightROISerializer(roi)
        return Response(serializer.data)
    
    def put(self, request, pk):
        roi = get_object_or_404(LightROI, pk=pk)
        serializer = LightROISerializer(roi, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        roi = get_object_or_404(LightROI, pk=pk)
        roi.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResponsibleOrgListCreateView(APIView):
    def get(self, request):
        orgs = ResponsibleOrg.objects.all()
        serializer = ResponsibleOrgSerializer(orgs, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ResponsibleOrgSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResponsibleOrgDetailView(APIView):
    def get(self, request, pk):
        org = get_object_or_404(ResponsibleOrg, pk=pk)
        serializer = ResponsibleOrgSerializer(org)
        return Response(serializer.data)
    
    def put(self, request, pk):
        org = get_object_or_404(ResponsibleOrg, pk=pk)
        serializer = ResponsibleOrgSerializer(org, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        org = get_object_or_404(ResponsibleOrg, pk=pk)
        org.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CallRequestTimelineListCreateView(APIView):
    def get(self, request):
        timelines = CallRequestTimeline.objects.all()
        serializer = CallRequestTimelineSerializer(timelines, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = CallRequestTimelineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CallRequestTimelineDetailView(APIView):
    def get(self, request, pk):
        timeline = get_object_or_404(CallRequestTimeline, pk=pk)
        serializer = CallRequestTimelineSerializer(timeline)
        return Response(serializer.data)
    
    def put(self, request, pk):
        timeline = get_object_or_404(CallRequestTimeline, pk=pk)
        serializer = CallRequestTimelineSerializer(timeline, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        timeline = get_object_or_404(CallRequestTimeline, pk=pk)
        timeline.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationListCreateView(APIView):
    def get(self, request):
        notifications = Notification.objects.all()
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationDetailView(APIView):
    def get(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    
    def put(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        serializer = NotificationSerializer(notification, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportEntryListCreateView(APIView):
    def get(self, request):
        entries = ReportEntry.objects.all()
        serializer = ReportEntrySerializer(entries, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ReportEntrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReportEntryDetailView(APIView):
    def get(self, request, pk):
        entry = get_object_or_404(ReportEntry, pk=pk)
        serializer = ReportEntrySerializer(entry)
        return Response(serializer.data)
    
    def put(self, request, pk):
        entry = get_object_or_404(ReportEntry, pk=pk)
        serializer = ReportEntrySerializer(entry, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        entry = get_object_or_404(ReportEntry, pk=pk)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UtilityNodeListCreateView(APIView):
    def get(self, request):
        # UtilityNode model doesn't have organization field, so return all nodes
        # In the future, if organization support is needed, add organization ForeignKey to the model
        nodes = UtilityNode.objects.all()
        
        serializer = UtilityNodeSerializer(nodes, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session
        data = request.data.copy()  # Always initialize data
        org_id = request.session.get('organization_id')
        if org_id:
            # Add organization to the request data
            data['organization'] = org_id
        
        serializer = UtilityNodeSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UtilityNodeDetailView(APIView):
    def get(self, request, pk):
        node = get_object_or_404(UtilityNode, pk=pk)
        serializer = UtilityNodeSerializer(node)
        return Response(serializer.data)
    
    def put(self, request, pk):
        node = get_object_or_404(UtilityNode, pk=pk)
        serializer = UtilityNodeSerializer(node, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        node = get_object_or_404(UtilityNode, pk=pk)
        node.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_bin_with_camera_image(request, pk):
    """
    API endpoint to update waste bin with camera image and AI analysis
    """
    bin = get_object_or_404(WasteBin, pk=pk)
    
    # Check if user has permission to access this bin
    org_id = request.session.get('organization_id')
    if org_id and str(bin.organization_id) != org_id:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get image data from request
    image_data = request.data.get('image_url', None)
    image_source = request.data.get('image_source', 'CCTV')
    last_analysis = request.data.get('last_analysis', f'Kamera tahlili {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    if image_data:
        # Update the bin with the new image and information
        bin.image_url = image_data
        bin.image_source = image_source
        bin.last_analysis = last_analysis
        
        # For camera images, we'll update the fill level based on the image if possible
        # In a real system, this would call an AI service to analyze the image
        # For now, we'll keep the existing fill level and is_full status
        # But we can enhance this to use AI analysis
        try:
            # Attempt to download and analyze the image with AI
            import requests as req
            import base64
            from io import BytesIO
            
            # Download image from URL
            response = req.get(image_data)
            if response.status_code == 200:
                # Convert image to base64 for AI analysis
                image_bytes = BytesIO(response.content).read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                
                # Call backend AI service to analyze the image
                ai_result = analyze_bin_image_backend(image_base64)
                
                # Update bin status based on AI analysis
                bin.fill_level = ai_result['fillLevel']
                bin.is_full = ai_result['isFull']
                
                # Update last analysis with AI results
                bin.last_analysis = f"AI tahlili: {ai_result['notes']}, IsFull: {ai_result['isFull']}, FillLevel: {ai_result['fillLevel']}%, Conf: {ai_result['confidence']}%"
                
        except Exception as e:
            # If AI analysis fails, log the error but continue with existing values
            print(f"AI analysis failed: {e}")
            # Optionally, you could use a default analysis or keep the existing values
            
        bin.save()
    
    serializer = WasteBinSerializer(bin)
    return Response(serializer.data)

def analyze_bin_image_backend(base64_image):
    """
    Backend function to analyze waste bin image using Google AI API
    """
    import os
    import requests
    import json
    
    # Get API key from environment or use default
    api_key = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
    if api_key == 'YOUR_API_KEY_HERE':
        # If no API key is set, return a basic response
        return {
            'isFull': True,
            'fillLevel': 90,
            'confidence': 70,
            'notes': 'API kaliti ornatilmagan, oddiy tahlil amalga oshirildi'
        }
    
    # Prepare the request to Google AI
    ai_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={api_key}'
    
    # Create detailed prompt for AI with enhanced analysis
    prompt = '''Siz tajriboli atrof-muhitni kuzatuv tizimi ekspertisiz. Rasmni tahlil qiling va quyidagilarni aniqlang:
    1. Rasmda chiqindi konteyneri bormi? Javob: HA yoki YO'Q.
    2. Agar HA bo'lsa, konteyner to'la bo'limi? Javob: HA yoki YO'Q.
    3. Agar HA bo'lsa, to'ldirish darajasini % (0-100) ko'rsating.
    4. Rasm sifatini baholang (yaxshi, o'rtacha, yomon).

    Javobni quyidagi JSON formatda bering:
    {
        "isFull": boolean,
        "fillLevel": number (0 dan 100 gacha foiz),
        "confidence": number (O'z qaroringga ishonch darajasi 0-100),
        "notes": string (Qisqa izoh o'zbek tilida: Masalan "Konteyner toshib ketgan" yoki "Yarmi bo'sh")
    }
    '''
    
    ai_headers = {
        'Content-Type': 'application/json',
    }
    
    ai_payload = {
        'contents': [{
            'parts': [
                {'text': prompt},
                {
                    'inlineData': {
                        'mimeType': 'image/jpeg',
                        'data': base64_image
                    }
                }
            ]
        }]
    }
    
    try:
        response = requests.post(ai_url, headers=ai_headers, data=json.dumps(ai_payload))
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the AI response
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    content_parts = candidate['content']['parts']
                    for part in content_parts:
                        if 'text' in part:
                            # Try to parse the JSON response
                            text_content = part['text'].strip()
                            
                            # Remove any markdown code block markers
                            if text_content.startswith('```'):
                                # Find the JSON part in the response
                                import re
                                json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
                                if json_match:
                                    text_content = json_match.group()
                                else:
                                    # If no JSON found, return default values
                                    return {
                                        'isFull': True,
                                        'fillLevel': 80,
                                        'confidence': 60,
                                        'notes': 'Tahlil natijasini tahlil qilishda xatolik yuz berdi'
                                    }
                            
                            try:
                                ai_result = json.loads(text_content)
                                return {
                                    'isFull': ai_result.get('isFull', False),
                                    'fillLevel': ai_result.get('fillLevel', 50),
                                    'confidence': ai_result.get('confidence', 50),
                                    'notes': ai_result.get('notes', 'AI tahlili tugadi')
                                }
                            except json.JSONDecodeError:
                                # If JSON parsing fails, return default values
                                return {
                                    'isFull': True,
                                    'fillLevel': 75,
                                    'confidence': 50,
                                    'notes': 'JSON javobini tahlil qilishda xatolik yuz berdi'
                                }
            
            # If no candidates found, return default values
            return {
                'isFull': True,
                'fillLevel': 70,
                'confidence': 40,
                'notes': 'AI javob topilmadi'
            }
        else:
            # If API call fails, return default values
            print(f"AI API request failed: {response.status_code}, {response.text}")
            return {
                'isFull': True,
                'fillLevel': 60,
                'confidence': 30,
                'notes': f'AI tahlilida xatolik: {response.status_code}'
            }
    except Exception as e:
        # If any error occurs, return default values
        print(f"AI analysis error: {e}")
        return {
            'isFull': True,
            'fillLevel': 50,
            'confidence': 25,
            'notes': f'AI tahlilida xatolik yuz berdi: {str(e)}'
        }

@csrf_exempt
@api_view(['POST', 'OPTIONS'])
@permission_classes([])  # Allow unauthenticated access for IoT sensor data
def update_iot_sensor_data(request):
    """
    API endpoint to update IoT sensor data (temperature and humidity) from ESP devices
    """
    try:
        # Log incoming request for debugging
        logger.info(f"📡 IoT sensor data received: {request.data}")
        logger.info(f"📡 Request from IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
        
        device_id = request.data.get('device_id')
        temperature = request.data.get('temperature')
        humidity = request.data.get('humidity')
        sleep_seconds = request.data.get('sleep_seconds', 2000)
        timestamp = request.data.get('timestamp', int(timezone.now().timestamp()))
        
        if not device_id:
            logger.error("❌ device_id is missing in request")
            return Response({'error': 'device_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the IoT device by device_id (case-insensitive search)
        try:
            # Try exact match first
            try:
                iot_device = IoTDevice.objects.get(device_id=device_id)
            except IoTDevice.DoesNotExist:
                # Try case-insensitive search
                iot_device = IoTDevice.objects.filter(device_id__iexact=device_id).first()
                if not iot_device:
                    raise IoTDevice.DoesNotExist
            
            logger.info(f"✅ Found IoT device: {device_id} (actual: {iot_device.device_id})")
        except IoTDevice.DoesNotExist:
            logger.error(f"❌ Device with ID {device_id} not found in database")
            # List available devices for debugging
            available_devices = list(IoTDevice.objects.values_list('device_id', flat=True))
            logger.info(f"📋 Available devices ({len(available_devices)} total): {available_devices}")
            return Response({
                'error': f'Device with ID "{device_id}" not found',
                'available_devices': available_devices,
                'hint': 'Check device_id spelling and case sensitivity'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate temperature and humidity ranges
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                try:
                    temperature = float(temperature)
                except (ValueError, TypeError):
                    logger.error(f"❌ Invalid temperature value: {temperature}")
                    return Response({'error': 'temperature must be a number'}, status=status.HTTP_400_BAD_REQUEST)
            # Temperature should be between -50 and 100 degrees Celsius
            if temperature < -50 or temperature > 100:
                logger.warning(f"⚠️ Temperature out of normal range: {temperature}°C")
        
        if humidity is not None:
            if not isinstance(humidity, (int, float)):
                try:
                    humidity = float(humidity)
                except (ValueError, TypeError):
                    logger.error(f"❌ Invalid humidity value: {humidity}")
                    return Response({'error': 'humidity must be a number'}, status=status.HTTP_400_BAD_REQUEST)
            # Humidity should be between 0 and 100 percent
            if humidity < 0 or humidity > 100:
                logger.warning(f"⚠️ Humidity out of normal range: {humidity}%")
        
        # Update device's last seen time and sensor readings
        iot_device.last_seen = timezone.now()
        if temperature is not None:
            iot_device.current_temperature = temperature
        if humidity is not None:
            iot_device.current_humidity = humidity
        iot_device.last_sensor_update = timezone.now()
        iot_device.save()
        logger.info(f"✅ Updated IoT device {device_id}: temp={temperature}°C, humidity={humidity}%")
        
        # Update associated room or boiler if available
        updated_entities = []
        if iot_device.room:
            if temperature is not None:
                iot_device.room.temperature = temperature
            if humidity is not None:
                iot_device.room.humidity = humidity
            iot_device.room.last_updated = timezone.now()
            iot_device.room.save()
            updated_entities.append(f"Room {iot_device.room.id}")
            logger.info(f"✅ Updated room {iot_device.room.id}")
        elif iot_device.boiler:
            if temperature is not None:
                iot_device.boiler.temperature = temperature
            if humidity is not None:
                iot_device.boiler.humidity = humidity
            iot_device.boiler.last_updated = timezone.now()
            iot_device.boiler.save()
            updated_entities.append(f"Boiler {iot_device.boiler.id}")
            logger.info(f"✅ Updated boiler {iot_device.boiler.id}")
        else:
            logger.warning(f"⚠️ IoT device {device_id} is not linked to any room or boiler")
        
        return Response({
            'message': 'Sensor data updated successfully',
            'device_id': device_id,
            'temperature': temperature,
            'humidity': humidity,
            'timestamp': timestamp,
            'updated_entities': updated_entities
        })
        
    except Exception as e:
        logger.error(f"❌ Error updating IoT sensor data: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST', 'OPTIONS'])
@permission_classes([])  # Temporarily allow unauthenticated for diagnostic tests
def link_iot_device_to_boiler(request):
    """
    API endpoint to link an IoT device to a boiler
    """
    try:
        # Diagnostic logging
        logger.debug('link_iot_device_to_boiler called with method=%s, user=%s', request.method, str(request.user))
        try:
            headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
        except Exception:
            headers = {}
        logger.debug('Request headers (HTTP_*): %s', headers)
        logger.debug('Request data: %s', request.data)

        device_id = request.data.get('device_id')
        boiler_id = request.data.get('boiler_id')
        
        if not device_id or not boiler_id:
            return Response({'error': 'device_id and boiler_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the IoT device and boiler
        try:
            iot_device = IoTDevice.objects.get(device_id=device_id)
        except IoTDevice.DoesNotExist:
            return Response({'error': f'Device with ID {device_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            boiler = Boiler.objects.get(id=boiler_id)
        except Boiler.DoesNotExist:
            return Response({'error': f'Boiler with ID {boiler_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Link the IoT device to the boiler
        iot_device.boiler = boiler
        iot_device.room = None  # Clear room if previously linked
        iot_device.save()
        
        # Update boiler with current device readings if available
        if iot_device.current_temperature is not None:
            boiler.temperature = iot_device.current_temperature
        if iot_device.current_humidity is not None:
            boiler.humidity = iot_device.current_humidity
        boiler.last_updated = timezone.now()
        boiler.save()

        logger.debug('IoT device %s linked to boiler %s successfully', device_id, boiler_id)
        return Response({
            'message': 'IoT device linked to boiler successfully',
            'device_id': device_id,
            'boiler_id': boiler_id
        })
        
    except Exception as e:
        logger.exception('Error in link_iot_device_to_boiler')
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Debug endpoint to verify POST requests reach the server
@csrf_exempt
@api_view(['POST', 'OPTIONS'])
@permission_classes([])
def iot_link_test(request):
    """Simple debug endpoint: echoes back received JSON and headers."""
    logger.debug('iot_link_test method=%s headers=%s data=%s', request.method, {k:v for k,v in request.META.items() if k.startswith('HTTP_')}, request.data)
    return Response({'ok': True, 'method': request.method, 'data': request.data})


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(['POST', 'OPTIONS'])
@permission_classes([])  # Temporarily allow unauthenticated for diagnostic tests
def link_iot_device_to_room(request):
    """
    API endpoint to link an IoT device to a room
    """
    try:
        # Diagnostic logging
        logger.debug('link_iot_device_to_room called with method=%s, user=%s', request.method, str(request.user))
        try:
            # Only log a subset of headers to avoid sensitive info
            headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
        except Exception:
            headers = {}
        logger.debug('Request headers (HTTP_*): %s', headers)
        logger.debug('Request data: %s', request.data)

        device_id = request.data.get('device_id')
        room_id = request.data.get('room_id')
        
        if not device_id or not room_id:
            return Response({'error': 'device_id and room_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the IoT device and room
        try:
            iot_device = IoTDevice.objects.get(device_id=device_id)
        except IoTDevice.DoesNotExist:
            return Response({'error': f'Device with ID {device_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response({'error': f'Room with ID {room_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Link the IoT device to the room
        iot_device.room = room
        iot_device.boiler = None  # Clear boiler if previously linked
        iot_device.save()
        
        # Update room with current device readings if available
        if iot_device.current_temperature is not None:
            room.temperature = iot_device.current_temperature
        if iot_device.current_humidity is not None:
            room.humidity = iot_device.current_humidity
        room.last_updated = timezone.now()
        room.save()
        
        logger.debug('IoT device %s linked to room %s successfully', device_id, room_id)
        return Response({
            'message': 'IoT device linked to room successfully',
            'device_id': device_id,
            'room_id': room_id
        })
        
    except Exception as e:
        logger.exception('Error in link_iot_device_to_room')
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# IoT Device Views
@method_decorator(csrf_exempt, name='dispatch')
class IoTDeviceListCreateView(APIView):
    permission_classes = []  # Allow unauthenticated access for IoT devices
    
    def get(self, request):
        # IoTDevice model doesn't have organization field, so return all devices
        # IoT devices are linked to rooms or boilers which are linked to facilities
        devices = IoTDevice.objects.select_related('location', 'room', 'boiler').all().distinct()
        
        # Remove duplicates by ID
        unique_devices = {}
        for device in devices:
            if device.id not in unique_devices:
                unique_devices[device.id] = device
        
        unique_devices_list = list(unique_devices.values())
        
        serializer = IoTDeviceSerializer(unique_devices_list, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        # Add organization context based on user session if needed
        # For IoT devices, we don't directly associate with organizations
        # but rather through rooms/boilers
        data = request.data.copy()  # Always initialize data
        
        serializer = IoTDeviceSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IoTDeviceDetailView(APIView):
    def get(self, request, pk):
        device = get_object_or_404(IoTDevice.objects.select_related('location', 'room', 'boiler'), pk=pk)
        serializer = IoTDeviceSerializer(device, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        device = get_object_or_404(IoTDevice, pk=pk)
        serializer = IoTDeviceSerializer(device, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        device = get_object_or_404(IoTDevice, pk=pk)
        serializer = IoTDeviceSerializer(device, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        device = get_object_or_404(IoTDevice, pk=pk)
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== NEW VIEWS FOR ENHANCED FUNCTIONALITY ====================

class WasteTaskListCreateView(APIView):
    """Waste collection task management"""
    def get(self, request):
        org_id = request.session.get('organization_id')
        if org_id:
            tasks = WasteTask.objects.filter(waste_bin__organization_id=org_id)
        else:
            tasks = WasteTask.objects.all()
        serializer = WasteTaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = WasteTaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WasteTaskDetailView(APIView):
    """Update and manage individual tasks"""
    def get(self, request, pk):
        task = get_object_or_404(WasteTask, pk=pk)
        serializer = WasteTaskSerializer(task)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        task = get_object_or_404(WasteTask, pk=pk)
        serializer = WasteTaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        task = get_object_or_404(WasteTask, pk=pk)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def auto_assign_task(request):
    """Automatically assign task to nearest available truck"""
    bin_id = request.data.get('bin_id')
    if not bin_id:
        return Response({'error': 'bin_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    waste_bin = get_object_or_404(WasteBin, pk=bin_id)
    
    # Find nearest idle truck in same toza hudud
    from math import radians, sin, cos, sqrt, atan2
    
    def calculate_distance(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    idle_trucks = Truck.objects.filter(
        status='IDLE',
        toza_hudud=waste_bin.toza_hudud
    )
    
    if not idle_trucks.exists():
        return Response({'error': 'No available trucks'}, status=status.HTTP_404_NOT_FOUND)
    
    # Find closest truck
    closest_truck = None
    min_distance = float('inf')
    
    for truck in idle_trucks:
        distance = calculate_distance(
            waste_bin.location.lat, waste_bin.location.lng,
            truck.location.lat, truck.location.lng
        )
        if distance < min_distance:
            min_distance = distance
            closest_truck = truck
    
    # Create task
    task = WasteTask.objects.create(
        waste_bin=waste_bin,
        assigned_truck=closest_truck,
        status='ASSIGNED',
        assigned_at=timezone.now(),
        priority='HIGH' if waste_bin.fill_level > 90 else 'MEDIUM'
    )
    
    # Update truck status
    closest_truck.status = 'BUSY'
    closest_truck.save()
    
    return Response({
        'task': WasteTaskSerializer(task).data,
        'distance': round(min_distance, 2)
    })


class RouteOptimizationView(APIView):
    """Generate optimized route for truck"""
    def post(self, request):
        truck_id = request.data.get('truck_id')
        bin_ids = request.data.get('bin_ids', [])
        
        if not truck_id:
            return Response({'error': 'truck_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        truck = get_object_or_404(Truck, pk=truck_id)
        
        # Simple greedy algorithm for route optimization
        # In production, use Google Maps Directions API
        from math import radians, sin, cos, sqrt, atan2
        
        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
        
        bins = WasteBin.objects.filter(id__in=bin_ids, toza_hudud=truck.toza_hudud)
        if not bins.exists():
            return Response({'error': 'No bins found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Greedy nearest neighbor algorithm
        unvisited = list(bins)
        route = []
        current_location = truck.location
        total_distance = 0
        
        while unvisited:
            nearest = None
            min_dist = float('inf')
            
            for bin in unvisited:
                dist = calculate_distance(
                    current_location.lat, current_location.lng,
                    bin.location.lat, bin.location.lng
                )
                if dist < min_dist:
                    min_dist = dist
                    nearest = bin
            
            route.append(str(nearest.id))
            total_distance += min_dist
            current_location = nearest.location
            unvisited.remove(nearest)
        
        # Estimate time and fuel
        avg_speed = 30  # km/h in city
        estimated_time = int((total_distance / avg_speed) * 60)  # minutes
        fuel_estimate = total_distance * 0.15  # liters (assuming 15L/100km)
        
        # Save route
        route_opt = RouteOptimization.objects.create(
            truck=truck,
            waypoints=route,
            total_distance=round(total_distance, 2),
            estimated_time=estimated_time,
            fuel_estimate=round(fuel_estimate, 2)
        )
        
        return Response(RouteOptimizationSerializer(route_opt).data)


class AlertNotificationListCreateView(APIView):
    """Alert notification management"""
    def get(self, request):
        org_id = request.session.get('organization_id')
        if org_id:
            alerts = AlertNotification.objects.filter(
                models.Q(related_waste_bin__organization_id=org_id) |
                models.Q(related_facility__organization_id=org_id) |
                models.Q(related_truck__organization_id=org_id)
            )
        else:
            alerts = AlertNotification.objects.all()
        serializer = AlertNotificationSerializer(alerts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = AlertNotificationSerializer(data=request.data)
        if serializer.is_valid():
            alert = serializer.save()
            
            # Trigger actual notification sending (SMS/Telegram/Email)
            # This would integrate with external services
            # For now, just mark as sent
            alert.is_sent = True
            alert.sent_at = timezone.now()
            alert.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClimateScheduleListCreateView(APIView):
    """Climate control schedules"""
    def get(self, request):
        schedules = ClimateSchedule.objects.all()
        serializer = ClimateScheduleSerializer(schedules, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ClimateScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClimateScheduleDetailView(APIView):
    """Manage individual schedules"""
    def get(self, request, pk):
        schedule = get_object_or_404(ClimateSchedule, pk=pk)
        serializer = ClimateScheduleSerializer(schedule)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        schedule = get_object_or_404(ClimateSchedule, pk=pk)
        serializer = ClimateScheduleSerializer(schedule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        schedule = get_object_or_404(ClimateSchedule, pk=pk)
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def generate_energy_report(request):
    """Generate energy report for a facility"""
    facility_id = request.data.get('facility_id')
    report_type = request.data.get('report_type', 'MONTHLY')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    
    if not facility_id:
        return Response({'error': 'facility_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    facility = get_object_or_404(Facility, pk=facility_id)
    
    from datetime import datetime, timedelta
    if not start_date or not end_date:
        end = datetime.now().date()
        if report_type == 'DAILY':
            start = end - timedelta(days=1)
        elif report_type == 'WEEKLY':
            start = end - timedelta(days=7)
        elif report_type == 'MONTHLY':
            start = end - timedelta(days=30)
        else:  # YEARLY
            start = end - timedelta(days=365)
    else:
        from django.utils.dateparse import parse_date
        start = parse_date(start_date)
        end = parse_date(end_date)
    
    # Calculate metrics (simplified - in production, this would query actual sensor data)
    total_energy = facility.energy_usage * (end - start).days
    total_cost = total_energy * 500  # Price per kWh
    avg_temp = 21.5  # Would come from sensor data
    avg_humidity = 50.0
    
    report = EnergyReport.objects.create(
        facility=facility,
        report_type=report_type,
        start_date=start,
        end_date=end,
        total_energy_kwh=total_energy,
        total_cost=total_cost,
        average_temperature=avg_temp,
        average_humidity=avg_humidity,
        efficiency_score=facility.efficiency_score,
        cost_savings=0,
        recommendations="Kechki soatlarda haroratni 2 darajaga pasaytiring. Energiya tejash: ~15%"
    )
    
    return Response(EnergyReportSerializer(report).data)


@api_view(['POST'])
def generate_waste_prediction(request):
    """Generate AI prediction for waste bin fill level"""
    bin_id = request.data.get('bin_id')
    days_ahead = request.data.get('days_ahead', 7)
    
    if not bin_id:
        return Response({'error': 'bin_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    waste_bin = get_object_or_404(WasteBin, pk=bin_id)
    
    # Simple linear prediction based on fill_rate
    # In production, use ML model with historical data
    from datetime import datetime, timedelta
    predictions = []
    
    for day in range(1, days_ahead + 1):
        prediction_date = (datetime.now() + timedelta(days=day)).date()
        predicted_level = min(100, waste_bin.fill_level + (waste_bin.fill_rate * day))
        
        prediction = WastePrediction.objects.create(
            waste_bin=waste_bin,
            prediction_date=prediction_date,
            predicted_fill_level=int(predicted_level),
            confidence=85.0,
            will_be_full=predicted_level >= 80,
            recommended_collection_date=prediction_date if predicted_level >= 80 else None,
            based_on_data_points=30
        )
        predictions.append(prediction)
    
    return Response(WastePredictionSerializer(predictions, many=True).data)


@api_view(['GET'])
def get_driver_performance(request, truck_id):
    """Get performance metrics for a driver"""
    truck = get_object_or_404(Truck, pk=truck_id)
    
    # Get last 30 days performance
    from datetime import datetime, timedelta
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    performance = DriverPerformance.objects.filter(
        truck=truck,
        date__gte=start_date,
        date__lte=end_date
    )
    
    serializer = DriverPerformanceSerializer(performance, many=True)
    
    # Calculate summary
    total_bins = sum(p.bins_collected for p in performance)
    total_distance = sum(p.total_distance for p in performance)
    avg_rating = sum(p.rating for p in performance) / len(performance) if performance else 0
    
    return Response({
        'performance': serializer.data,
        'summary': {
            'total_bins_collected': total_bins,
            'total_distance_km': round(total_distance, 2),
            'average_rating': round(avg_rating, 2),
            'days_worked': len(performance)
        }
    })


@api_view(['GET'])
def get_waste_statistics(request):
    """Get comprehensive waste management statistics"""
    org_id = request.session.get('organization_id')
    
    from datetime import datetime, timedelta
    from django.db.models import Count, Avg, Sum
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    if org_id:
        bins = WasteBin.objects.filter(organization_id=org_id)
        trucks = Truck.objects.filter(organization_id=org_id)
        tasks = WasteTask.objects.filter(waste_bin__organization_id=org_id, created_at__gte=start_date)
    else:
        bins = WasteBin.objects.all()
        trucks = Truck.objects.all()
        tasks = WasteTask.objects.filter(created_at__gte=start_date)
    
    stats = {
        'total_bins': bins.count(),
        'full_bins': bins.filter(is_full=True).count(),
        'average_fill_level': bins.aggregate(Avg('fill_level'))['fill_level__avg'] or 0,
        'total_trucks': trucks.count(),
        'active_trucks': trucks.filter(status='BUSY').count(),
        'tasks_completed': tasks.filter(status='COMPLETED').count(),
        'tasks_pending': tasks.filter(status='PENDING').count(),
        'tasks_in_progress': tasks.filter(status='IN_PROGRESS').count(),
        'collection_efficiency': round((tasks.filter(status='COMPLETED').count() / tasks.count() * 100) if tasks.count() > 0 else 0, 2),
        'by_hudud': {}
    }
    
    # Statistics by toza hudud
    for hudud in ['1-sonli Toza Hudud', '2-sonli Toza Hudud']:
        hudud_bins = bins.filter(toza_hudud=hudud)
        stats['by_hudud'][hudud] = {
            'total': hudud_bins.count(),
            'full': hudud_bins.filter(is_full=True).count(),
            'avg_fill': round(hudud_bins.aggregate(Avg('fill_level'))['fill_level__avg'] or 0, 2)
        }
    
    return Response(stats)


@api_view(['GET'])
def get_climate_statistics(request):
    """Get comprehensive climate control statistics"""
    from django.db.models import Avg, Count
    from datetime import datetime, timedelta
    
    facilities = Facility.objects.all()
    rooms = Room.objects.all()
    boilers = Boiler.objects.all()
    
    stats = {
        'total_facilities': facilities.count(),
        'total_rooms': rooms.count(),
        'total_boilers': boilers.count(),
        'average_temperature': round(rooms.aggregate(Avg('temperature'))['temperature__avg'] or 0, 2),
        'average_humidity': round(rooms.aggregate(Avg('humidity'))['humidity__avg'] or 0, 2),
        'critical_rooms': rooms.filter(status='CRITICAL').count(),
        'warning_rooms': rooms.filter(status='WARNING').count(),
        'optimal_rooms': rooms.filter(status='OPTIMAL').count(),
        'by_facility_type': {}
    }
    
    for ftype in ['SCHOOL', 'KINDERGARTEN', 'HOSPITAL']:
        type_facilities = facilities.filter(type=ftype)
        stats['by_facility_type'][ftype] = {
            'count': type_facilities.count(),
            'avg_efficiency': round(type_facilities.aggregate(Avg('efficiency_score'))['efficiency_score__avg'] or 0, 2)
        }
    
    return Response(stats)


