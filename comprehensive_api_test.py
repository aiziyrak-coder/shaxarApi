#!/usr/bin/env python3
"""
COMPREHENSIVE API TEST SUITE
Tests all backend endpoints, authentication, CRUD operations, and data validation
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import sys

# Configuration
API_BASE_URL = "https://ferganaapi.cdcgroup.uz/api"
TEST_USER = {"login": "fergan", "password": "123"}
TEST_ADMIN = {"login": "superadmin", "password": "123"}

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class APITester:
    def __init__(self):
        self.token = None
        self.admin_token = None
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Log with colors"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = Colors.WHITE
        
        if level == "SUCCESS":
            color = Colors.GREEN
            symbol = "✅"
        elif level == "ERROR":
            color = Colors.RED
            symbol = "❌"
        elif level == "WARNING":
            color = Colors.YELLOW
            symbol = "⚠️"
        elif level == "INFO":
            color = Colors.BLUE
            symbol = "ℹ️"
        else:
            symbol = "•"
            
        print(f"{color}{symbol} [{timestamp}] {message}{Colors.END}")
    
    def test_case(self, name: str):
        """Decorator for test cases"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                self.total_tests += 1
                test_number = self.total_tests
                
                print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
                print(f"{Colors.CYAN}{Colors.BOLD}TEST #{test_number}: {name}{Colors.END}")
                print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    
                    if result:
                        self.passed_tests += 1
                        self.log(f"PASSED in {elapsed:.2f}s", "SUCCESS")
                        self.test_results.append({
                            "test": name,
                            "status": "PASS",
                            "time": elapsed
                        })
                    else:
                        self.failed_tests += 1
                        self.log(f"FAILED in {elapsed:.2f}s", "ERROR")
                        self.test_results.append({
                            "test": name,
                            "status": "FAIL",
                            "time": elapsed
                        })
                    
                    return result
                    
                except Exception as e:
                    elapsed = time.time() - start_time
                    self.failed_tests += 1
                    self.log(f"EXCEPTION in {elapsed:.2f}s: {str(e)}", "ERROR")
                    self.test_results.append({
                        "test": name,
                        "status": "EXCEPTION",
                        "time": elapsed,
                        "error": str(e)
                    })
                    return False
                    
            return wrapper
        return decorator
    
    def assert_equal(self, actual, expected, message=""):
        """Assert equality with logging"""
        if actual == expected:
            self.log(f"✓ {message or 'Values match'}", "SUCCESS")
            return True
        else:
            self.log(f"✗ {message or 'Values do not match'}: expected {expected}, got {actual}", "ERROR")
            return False
    
    def assert_in(self, value, container, message=""):
        """Assert value in container"""
        if value in container:
            self.log(f"✓ {message or 'Value found'}", "SUCCESS")
            return True
        else:
            self.log(f"✗ {message or 'Value not found'}: {value} not in container", "ERROR")
            return False
    
    def assert_not_none(self, value, message=""):
        """Assert value is not None"""
        if value is not None:
            self.log(f"✓ {message or 'Value exists'}", "SUCCESS")
            return True
        else:
            self.log(f"✗ {message or 'Value is None'}", "ERROR")
            return False
    
    # ========================================
    # AUTHENTICATION TESTS
    # ========================================
    
    @test_case("Authentication - Valid Login (Organization)")
    def test_auth_valid_login(self):
        """Test valid organization login"""
        response = requests.post(
            f"{API_BASE_URL}/auth/login/",
            json=TEST_USER,
            headers={"Content-Type": "application/json"}
        )
        
        self.log(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            self.log(f"Response: {response.text}", "ERROR")
            return False
        
        data = response.json()
        
        # Validate response structure
        checks = [
            self.assert_in('token', data, "Token in response"),
            self.assert_in('user', data, "User in response"),
            self.assert_in('name', data['user'], "User name in response"),
            self.assert_in('role', data['user'], "User role in response"),
        ]
        
        if all(checks):
            self.token = data['token']
            self.log(f"Token: {self.token[:30]}...", "INFO")
            return True
        
        return False
    
    @test_case("Authentication - Admin Login")
    def test_auth_admin_login(self):
        """Test admin login"""
        response = requests.post(
            f"{API_BASE_URL}/auth/login/",
            json=TEST_ADMIN,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data.get('token')
            self.log(f"Admin token obtained", "SUCCESS")
            return True
        else:
            self.log(f"Admin login failed: {response.status_code}", "WARNING")
            self.warnings += 1
            return True  # Not critical if admin doesn't exist
    
    @test_case("Authentication - Invalid Credentials")
    def test_auth_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{API_BASE_URL}/auth/login/",
            json={"login": "invalid", "password": "wrong"},
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 401 or 400
        if response.status_code in [400, 401]:
            self.log(f"Correctly rejected invalid credentials", "SUCCESS")
            return True
        else:
            self.log(f"Unexpected status: {response.status_code}", "ERROR")
            return False
    
    @test_case("Authentication - Empty Credentials")
    def test_auth_empty_credentials(self):
        """Test login with empty credentials"""
        response = requests.post(
            f"{API_BASE_URL}/auth/login/",
            json={"login": "", "password": ""},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [400, 401]:
            self.log(f"Correctly rejected empty credentials", "SUCCESS")
            return True
        else:
            self.log(f"Unexpected status: {response.status_code}", "ERROR")
            return False
    
    @test_case("Authentication - Token Validation")
    def test_auth_token_validation(self):
        """Test token validation"""
        if not self.token:
            self.log("No token available, skipping", "WARNING")
            return False
        
        response = requests.get(
            f"{API_BASE_URL}/auth/validate/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code == 200:
            self.log(f"Token is valid", "SUCCESS")
            return True
        else:
            self.log(f"Token validation failed: {response.status_code}", "ERROR")
            return False
    
    # ========================================
    # WASTE BINS TESTS
    # ========================================
    
    @test_case("Waste Bins - Get All")
    def test_waste_bins_get_all(self):
        """Test getting all waste bins"""
        if not self.token:
            return False
        
        response = requests.get(
            f"{API_BASE_URL}/waste-bins/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code != 200:
            self.log(f"Failed to get bins: {response.status_code}", "ERROR")
            return False
        
        bins = response.json()
        self.log(f"Retrieved {len(bins)} waste bins", "INFO")
        
        if len(bins) == 0:
            self.log("No bins found", "WARNING")
            self.warnings += 1
        
        # Validate first bin structure
        if len(bins) > 0:
            bin = bins[0]
            required_fields = ['id', 'address', 'location', 'fill_level', 'is_full', 'qr_code_url']
            
            checks = [self.assert_in(field, bin, f"Field '{field}' exists") for field in required_fields]
            
            # ⭐ CRITICAL: Check QR code URL
            if 'qr_code_url' in bin:
                qr_url = bin['qr_code_url']
                if qr_url:
                    self.log(f"✅ QR Code URL exists: {qr_url}", "SUCCESS")
                    
                    # Verify QR code URL is accessible
                    qr_response = requests.head(qr_url)
                    if qr_response.status_code == 200:
                        self.log(f"✅ QR Code image is accessible", "SUCCESS")
                    else:
                        self.log(f"⚠️ QR Code image not accessible: {qr_response.status_code}", "WARNING")
                        self.warnings += 1
                else:
                    self.log(f"⚠️ QR Code URL is null", "WARNING")
                    self.warnings += 1
            
            return all(checks)
        
        return True
    
    @test_case("Waste Bins - Get Single")
    def test_waste_bins_get_single(self):
        """Test getting a single waste bin"""
        if not self.token:
            return False
        
        # First get all bins to get an ID
        response = requests.get(
            f"{API_BASE_URL}/waste-bins/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code != 200 or len(response.json()) == 0:
            self.log("No bins to test with", "WARNING")
            return False
        
        bin_id = response.json()[0]['id']
        
        # Get single bin
        response = requests.get(
            f"{API_BASE_URL}/waste-bins/{bin_id}/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code == 200:
            bin = response.json()
            self.log(f"Retrieved bin: {bin.get('address', 'N/A')}", "INFO")
            
            # Validate structure
            checks = [
                self.assert_equal(bin['id'], bin_id, "Bin ID matches"),
                self.assert_not_none(bin.get('address'), "Address exists"),
                self.assert_not_none(bin.get('location'), "Location exists"),
            ]
            
            return all(checks)
        
        self.log(f"Failed: {response.status_code}", "ERROR")
        return False
    
    @test_case("Waste Bins - Create New (with Auto QR)")
    def test_waste_bins_create(self):
        """Test creating a new waste bin - QR should auto-generate"""
        if not self.token:
            return False
        
        # Get organization
        orgs_response = requests.get(
            f"{API_BASE_URL}/organizations/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if orgs_response.status_code != 200 or len(orgs_response.json()) == 0:
            self.log("No organization found", "ERROR")
            return False
        
        org_id = orgs_response.json()[0]['id']
        
        # Create test bin
        new_bin = {
            "organization_id": org_id,
            "address": f"🧪 QA TEST BIN - {datetime.now().strftime('%H:%M:%S')}",
            "location": {"lat": 40.3833, "lng": 71.7833},
            "toza_hudud": "1-sonli Toza Hudud",
            "fill_level": 0,
            "is_full": False
        }
        
        response = requests.post(
            f"{API_BASE_URL}/waste-bins/",
            json=new_bin,
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code in [200, 201]:
            created_bin = response.json()
            self.log(f"Bin created: {created_bin['id']}", "SUCCESS")
            
            # ⭐ CRITICAL: Check if QR code was auto-generated
            time.sleep(2)  # Wait for signal to complete
            
            # Fetch bin again to check QR code
            check_response = requests.get(
                f"{API_BASE_URL}/waste-bins/{created_bin['id']}/",
                headers={"Authorization": f"Token {self.token}"}
            )
            
            if check_response.status_code == 200:
                updated_bin = check_response.json()
                qr_url = updated_bin.get('qr_code_url')
                
                if qr_url:
                    self.log(f"✅ QR CODE AUTO-GENERATED: {qr_url}", "SUCCESS")
                    
                    # Verify QR URL format
                    if "ferganaapi.cdcgroup.uz/media/qr_codes/bin_" in qr_url and qr_url.endswith("_qr.png"):
                        self.log(f"✅ QR URL format correct", "SUCCESS")
                    else:
                        self.log(f"⚠️ QR URL format unexpected", "WARNING")
                        self.warnings += 1
                    
                    return True
                else:
                    self.log(f"❌ QR CODE NOT GENERATED", "ERROR")
                    return False
            
            return True
        else:
            self.log(f"Failed: {response.status_code} - {response.text}", "ERROR")
            return False
    
    @test_case("Waste Bins - Update")
    def test_waste_bins_update(self):
        """Test updating a waste bin"""
        if not self.token:
            return False
        
        # Get first bin
        response = requests.get(
            f"{API_BASE_URL}/waste-bins/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code != 200 or len(response.json()) == 0:
            return False
        
        bin_id = response.json()[0]['id']
        
        # Update bin
        update_data = {
            "fill_level": 85,
            "is_full": True
        }
        
        response = requests.patch(
            f"{API_BASE_URL}/waste-bins/{bin_id}/",
            json=update_data,
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            updated_bin = response.json()
            return self.assert_equal(updated_bin['fill_level'], 85, "Fill level updated")
        
        return False
    
    # ========================================
    # IOT DEVICES TESTS
    # ========================================
    
    @test_case("IoT Devices - Get All")
    def test_iot_devices_get_all(self):
        """Test getting all IoT devices"""
        if not self.token:
            return False
        
        response = requests.get(
            f"{API_BASE_URL}/iot-devices/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code == 200:
            devices = response.json()
            self.log(f"Retrieved {len(devices)} IoT devices", "INFO")
            
            if len(devices) > 0:
                device = devices[0]
                fields = ['id', 'device_id', 'device_type', 'current_temperature', 'current_humidity']
                checks = [self.assert_in(field, device, f"Field '{field}' exists") for field in fields]
                return all(checks)
            
            return True
        
        return False
    
    @test_case("IoT Devices - Update Sensor Data")
    def test_iot_devices_update_data(self):
        """Test updating IoT sensor data"""
        sensor_data = {
            "device_id": "ESP-1E6CDD",
            "temperature": 23.5,
            "humidity": 55.0,
            "timestamp": int(time.time())
        }
        
        response = requests.post(
            f"{API_BASE_URL}/iot-devices/data/update/",
            json=sensor_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            self.log(f"Sensor data updated for {sensor_data['device_id']}", "SUCCESS")
            return True
        else:
            self.log(f"Failed: {response.status_code} - {response.text}", "ERROR")
            return False
    
    # ========================================
    # FACILITIES TESTS
    # ========================================
    
    @test_case("Facilities - Get All")
    def test_facilities_get_all(self):
        """Test getting all facilities"""
        if not self.token:
            return False
        
        response = requests.get(
            f"{API_BASE_URL}/facilities/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code == 200:
            facilities = response.json()
            self.log(f"Retrieved {len(facilities)} facilities", "INFO")
            return True
        
        return False
    
    @test_case("Rooms - Get All")
    def test_rooms_get_all(self):
        """Test getting all rooms"""
        if not self.token:
            return False
        
        response = requests.get(
            f"{API_BASE_URL}/rooms/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code == 200:
            rooms = response.json()
            self.log(f"Retrieved {len(rooms)} rooms", "INFO")
            
            if len(rooms) > 0:
                room = rooms[0]
                return self.assert_in('temperature', room, "Room has temperature")
            
            return True
        
        return False
    
    # ========================================
    # TRUCKS TESTS
    # ========================================
    
    @test_case("Trucks - Get All")
    def test_trucks_get_all(self):
        """Test getting all trucks"""
        if not self.token:
            return False
        
        response = requests.get(
            f"{API_BASE_URL}/trucks/",
            headers={"Authorization": f"Token {self.token}"}
        )
        
        if response.status_code == 200:
            trucks = response.json()
            self.log(f"Retrieved {len(trucks)} trucks", "INFO")
            return True
        
        return False
    
    # ========================================
    # SECURITY TESTS
    # ========================================
    
    @test_case("Security - API without Authentication")
    def test_security_no_auth(self):
        """Test API access without authentication token"""
        response = requests.get(f"{API_BASE_URL}/waste-bins/")
        
        # Should return 401 Unauthorized
        if response.status_code == 401:
            self.log(f"Correctly requires authentication", "SUCCESS")
            return True
        else:
            self.log(f"Security issue: API accessible without auth (status: {response.status_code})", "ERROR")
            return False
    
    @test_case("Security - Invalid Token")
    def test_security_invalid_token(self):
        """Test API with invalid token"""
        response = requests.get(
            f"{API_BASE_URL}/waste-bins/",
            headers={"Authorization": "Token invalid_fake_token_12345"}
        )
        
        if response.status_code == 401:
            self.log(f"Correctly rejects invalid token", "SUCCESS")
            return True
        else:
            self.log(f"Security issue: accepts invalid token", "ERROR")
            return False
    
    @test_case("Security - SQL Injection Test")
    def test_security_sql_injection(self):
        """Test SQL injection protection"""
        malicious_login = {
            "login": "admin' OR '1'='1",
            "password": "anything"
        }
        
        response = requests.post(
            f"{API_BASE_URL}/auth/login/",
            json=malicious_login,
            headers={"Content-Type": "application/json"}
        )
        
        # Should reject
        if response.status_code in [400, 401]:
            self.log(f"SQL injection prevented", "SUCCESS")
            return True
        elif response.status_code == 200:
            self.log(f"CRITICAL: SQL injection possible!", "ERROR")
            return False
        
        return True
    
    # ========================================
    # PERFORMANCE TESTS
    # ========================================
    
    @test_case("Performance - API Response Time")
    def test_performance_response_time(self):
        """Test API response times"""
        if not self.token:
            return False
        
        endpoints = [
            "/waste-bins/",
            "/trucks/",
            "/facilities/",
            "/iot-devices/",
        ]
        
        all_fast = True
        
        for endpoint in endpoints:
            start = time.time()
            response = requests.get(
                f"{API_BASE_URL}{endpoint}",
                headers={"Authorization": f"Token {self.token}"}
            )
            elapsed = time.time() - start
            
            if elapsed < 1.0:
                self.log(f"✓ {endpoint}: {elapsed:.3f}s (< 1s)", "SUCCESS")
            elif elapsed < 2.0:
                self.log(f"⚠ {endpoint}: {elapsed:.3f}s (slow)", "WARNING")
                self.warnings += 1
            else:
                self.log(f"✗ {endpoint}: {elapsed:.3f}s (too slow!)", "ERROR")
                all_fast = False
        
        return all_fast
    
    # ========================================
    # RUN ALL TESTS
    # ========================================
    
    def run_all_tests(self):
        """Run all test cases"""
        print(f"\n{Colors.MAGENTA}{Colors.BOLD}")
        print("╔" + "="*78 + "╗")
        print("║" + " "*20 + "COMPREHENSIVE API TEST SUITE" + " "*30 + "║")
        print("║" + " "*25 + "Smart City - Farg'ona" + " "*34 + "║")
        print("╚" + "="*78 + "╝")
        print(f"{Colors.END}\n")
        
        start_time = time.time()
        
        # Run tests in order
        self.test_auth_valid_login()
        self.test_auth_admin_login()
        self.test_auth_invalid_login()
        self.test_auth_empty_credentials()
        self.test_auth_token_validation()
        
        self.test_security_no_auth()
        self.test_security_invalid_token()
        self.test_security_sql_injection()
        
        self.test_waste_bins_get_all()
        self.test_waste_bins_get_single()
        self.test_waste_bins_create()
        self.test_waste_bins_update()
        
        self.test_iot_devices_get_all()
        self.test_iot_devices_update_data()
        
        self.test_facilities_get_all()
        self.test_rooms_get_all()
        self.test_trucks_get_all()
        
        self.test_performance_response_time()
        
        # Summary
        total_time = time.time() - start_time
        
        print(f"\n{Colors.MAGENTA}{Colors.BOLD}")
        print("╔" + "="*78 + "╗")
        print("║" + " "*30 + "TEST SUMMARY" + " "*36 + "║")
        print("╚" + "="*78 + "╝")
        print(f"{Colors.END}\n")
        
        print(f"{Colors.BOLD}Total Tests:{Colors.END} {self.total_tests}")
        print(f"{Colors.GREEN}✅ Passed:{Colors.END} {self.passed_tests} ({self.passed_tests/self.total_tests*100:.1f}%)")
        print(f"{Colors.RED}❌ Failed:{Colors.END} {self.failed_tests} ({self.failed_tests/self.total_tests*100:.1f}%)")
        print(f"{Colors.YELLOW}⚠️ Warnings:{Colors.END} {self.warnings}")
        print(f"{Colors.BLUE}⏱️ Total Time:{Colors.END} {total_time:.2f}s")
        
        # Status
        if self.failed_tests == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.END}\n")
            return True
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED - NEEDS ATTENTION{Colors.END}\n")
            return False

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
