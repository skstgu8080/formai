#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FormAI Enhanced Server - Full-featured Python server with API endpoints
"""

import os
import json
import sys
import subprocess
import threading
import time
import hashlib
import base64
import struct
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import mimetypes

# Fix Windows encoding issues
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class FormAIEnhancedHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.static_dir = "."
        self.profiles_dir = "profiles"
        super().__init__(*args, **kwargs)

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # WebSocket upgrade
        if path == '/ws':
            self.handle_websocket_upgrade()
            return

        # API Routes
        if path == '/api/profiles':
            self.handle_get_profiles()
        elif path.startswith('/api/profiles/'):
            profile_id = path.split('/')[-1]
            self.handle_get_profile(profile_id)
        elif path == '/api/settings':
            self.handle_get_settings()
        elif path == '/api/saved-urls':
            self.handle_get_saved_urls()
        elif path.startswith('/api/saved-urls/'):
            url_id = path.split('/')[-1]
            self.handle_get_saved_url(url_id)
        elif path == '/api/url-groups':
            self.handle_get_url_groups()
        else:
            # Serve static files
            self.serve_static_file(path)

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')

        if path == '/api/profiles':
            self.handle_create_profile(post_data)
        elif path == '/api/settings':
            self.handle_save_settings(post_data)
        elif path == '/api/settings/api-keys':
            self.handle_save_api_keys(post_data)
        elif path == '/api/saved-urls':
            self.handle_create_saved_url(post_data)
        else:
            self.send_error(404, 'Not Found')

    def do_PUT(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        content_length = int(self.headers.get('Content-Length', 0))
        put_data = self.rfile.read(content_length).decode('utf-8')

        if path.startswith('/api/profiles/'):
            profile_id = path.split('/')[-1]
            self.handle_update_profile(profile_id, put_data)
        elif path.startswith('/api/saved-urls/'):
            url_id = path.split('/')[-1]
            self.handle_update_saved_url(url_id, put_data)
        else:
            self.send_error(404, 'Not Found')

    def do_DELETE(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path.startswith('/api/profiles/'):
            profile_id = path.split('/')[-1]
            self.handle_delete_profile(profile_id)
        elif path.startswith('/api/saved-urls/'):
            url_id = path.split('/')[-1]
            self.handle_delete_saved_url(url_id)
        elif path == '/api/saved-urls':
            self.handle_clear_saved_urls()
        else:
            self.send_error(404, 'Not Found')

    def handle_get_profiles(self):
        """Get all profiles from the profiles directory"""
        profiles = []
        if os.path.exists(self.profiles_dir):
            for filename in os.listdir(self.profiles_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.profiles_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            profile_data = json.load(f)
                            # Handle different profile structures
                            if 'data' in profile_data:
                                # Old structure with nested data
                                data = profile_data['data']
                                profile = {
                                    'id': profile_data.get('id', filename[:-5]),
                                    'name': profile_data.get('name', 'Unnamed Profile'),
                                    'email': data.get('email', ''),
                                    'firstName': data.get('firstName', ''),
                                    'lastName': data.get('lastName', ''),
                                    'phone': data.get('phone', ''),
                                    'company': data.get('company', ''),
                                    'address': data.get('address', ''),
                                    'city': data.get('city', ''),
                                    'state': data.get('state', ''),
                                    'zipCode': data.get('zipCode', ''),
                                    'country': data.get('country', ''),
                                    'createdAt': profile_data.get('created_at', ''),
                                    'updatedAt': profile_data.get('updated_at', '')
                                }
                            else:
                                # Flat structure like chris.json
                                profile = {
                                    'id': profile_data.get('id', filename[:-5]),
                                    'name': profile_data.get('profileName', profile_data.get('name', 'Unnamed Profile')),
                                    'title': profile_data.get('title', ''),
                                    'firstName': profile_data.get('firstName', ''),
                                    'middleInitial': profile_data.get('middleInitial', ''),
                                    'lastName': profile_data.get('lastName', ''),
                                    'fullName': profile_data.get('fullName', ''),
                                    'company': profile_data.get('company', ''),
                                    'position': profile_data.get('position', ''),
                                    'address1': profile_data.get('address1', ''),
                                    'address2': profile_data.get('address2', ''),
                                    'city': profile_data.get('city', ''),
                                    'state': profile_data.get('state', ''),
                                    'country': profile_data.get('country', ''),
                                    'zip': profile_data.get('zip', ''),
                                    'homePhone': profile_data.get('homePhone', ''),
                                    'workPhone': profile_data.get('workPhone', ''),
                                    'cellPhone': profile_data.get('cellPhone', ''),
                                    'fax': profile_data.get('fax', ''),
                                    'email': profile_data.get('email', ''),
                                    'website': profile_data.get('website', ''),
                                    'username': profile_data.get('username', ''),
                                    'password': profile_data.get('password', ''),
                                    'creditCardType': profile_data.get('creditCardType', ''),
                                    'creditCardNumber': profile_data.get('creditCardNumber', ''),
                                    'creditCardExpMonth': profile_data.get('creditCardExpMonth', ''),
                                    'creditCardExpYear': profile_data.get('creditCardExpYear', ''),
                                    'creditCardCVC': profile_data.get('creditCardCVC', ''),
                                    'creditCardName': profile_data.get('creditCardName', ''),
                                    'creditCardBank': profile_data.get('creditCardBank', ''),
                                    'creditCardServicePhone': profile_data.get('creditCardServicePhone', ''),
                                    'sex': profile_data.get('sex', ''),
                                    'ssn': profile_data.get('ssn', ''),
                                    'driverLicense': profile_data.get('driverLicense', ''),
                                    'birthMonth': profile_data.get('birthMonth', ''),
                                    'birthDay': profile_data.get('birthDay', ''),
                                    'birthYear': profile_data.get('birthYear', ''),
                                    'age': profile_data.get('age', ''),
                                    'birthPlace': profile_data.get('birthPlace', ''),
                                    'income': profile_data.get('income', ''),
                                    'customMessage': profile_data.get('customMessage', ''),
                                    'comments': profile_data.get('comments', ''),
                                    'createdAt': profile_data.get('created_at', ''),
                                    'updatedAt': profile_data.get('updated_at', '')
                                }

                            # Add derived fields for compatibility
                            profile['phone'] = profile.get('homePhone') or profile.get('cellPhone') or profile.get('workPhone', '')
                            profile['address'] = profile.get('address1', '')
                            profiles.append(profile)
                    except Exception as e:
                        print(f"Error reading profile {filename}: {e}")

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.safe_write_response(json.dumps(profiles))

    def handle_get_profile(self, profile_id):
        """Get a specific profile"""
        filepath = os.path.join(self.profiles_dir, f"{profile_id}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                profile_data = json.load(f)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps(profile_data))
        else:
            self.send_error(404, 'Profile not found')

    def handle_create_profile(self, data):
        """Create a new profile"""
        try:
            profile_data = json.loads(data)
            profile_id = profile_data.get('id', f"profile-{int(time.time())}")

            # Structure the profile data in flat format
            profile = {
                'id': profile_id,
                'profileName': profile_data.get('name', 'Unnamed Profile'),
                'title': profile_data.get('title', ''),
                'firstName': profile_data.get('firstName', ''),
                'middleInitial': profile_data.get('middleInitial', ''),
                'lastName': profile_data.get('lastName', ''),
                'fullName': f"{profile_data.get('firstName', '')} {profile_data.get('middleInitial', '')} {profile_data.get('lastName', '')}".strip(),
                'company': profile_data.get('company', ''),
                'position': profile_data.get('position', ''),
                'address1': profile_data.get('address1', ''),
                'address2': profile_data.get('address2', ''),
                'city': profile_data.get('city', ''),
                'state': profile_data.get('state', ''),
                'country': profile_data.get('country', ''),
                'zip': profile_data.get('zip', ''),
                'homePhone': profile_data.get('homePhone', ''),
                'workPhone': profile_data.get('workPhone', ''),
                'cellPhone': profile_data.get('cellPhone', ''),
                'fax': profile_data.get('fax', ''),
                'email': profile_data.get('email', ''),
                'website': profile_data.get('website', ''),
                'username': profile_data.get('username', ''),
                'password': profile_data.get('password', ''),
                'creditCardType': profile_data.get('creditCardType', ''),
                'creditCardNumber': profile_data.get('creditCardNumber', ''),
                'creditCardExpMonth': profile_data.get('creditCardExpMonth', ''),
                'creditCardExpYear': profile_data.get('creditCardExpYear', ''),
                'creditCardCVC': profile_data.get('creditCardCVC', ''),
                'creditCardName': profile_data.get('creditCardName', ''),
                'creditCardBank': profile_data.get('creditCardBank', ''),
                'creditCardServicePhone': profile_data.get('creditCardServicePhone', ''),
                'sex': profile_data.get('sex', ''),
                'ssn': profile_data.get('ssn', ''),
                'driverLicense': profile_data.get('driverLicense', ''),
                'birthMonth': profile_data.get('birthMonth', ''),
                'birthDay': profile_data.get('birthDay', ''),
                'birthYear': profile_data.get('birthYear', ''),
                'age': profile_data.get('age', ''),
                'birthPlace': profile_data.get('birthPlace', ''),
                'income': profile_data.get('income', ''),
                'customMessage': profile_data.get('customMessage', ''),
                'comments': profile_data.get('comments', ''),
                'created_at': profile_data.get('createdAt', time.strftime('%Y-%m-%dT%H:%M:%SZ')),
                'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')
            }

            # Save to file
            if not os.path.exists(self.profiles_dir):
                os.makedirs(self.profiles_dir)

            filepath = os.path.join(self.profiles_dir, f"{profile_id}.json")
            with open(filepath, 'w') as f:
                json.dump(profile, f, indent=2)

            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps({'success': True, 'id': profile_id}))
        except Exception as e:
            self.send_error(400, f'Bad request: {str(e)}')

    def handle_update_profile(self, profile_id, data):
        """Update an existing profile"""
        try:
            filepath = os.path.join(self.profiles_dir, f"{profile_id}.json")
            if not os.path.exists(filepath):
                # If file doesn't exist, create it
                self.handle_create_profile(data)
                return

            profile_data = json.loads(data)

            # Load existing profile
            with open(filepath, 'r') as f:
                existing_profile = json.load(f)

            # Update the profile data - handle both old nested format and new flat format
            if 'data' in existing_profile:
                # Convert old format to new flat format
                old_data = existing_profile['data']
                existing_profile = {
                    'id': existing_profile.get('id', profile_id),
                    'profileName': profile_data.get('name', existing_profile.get('name', '')),
                    'title': profile_data.get('title', ''),
                    'firstName': profile_data.get('firstName', old_data.get('firstName', '')),
                    'middleInitial': profile_data.get('middleInitial', ''),
                    'lastName': profile_data.get('lastName', old_data.get('lastName', '')),
                    'fullName': f"{profile_data.get('firstName', '')} {profile_data.get('middleInitial', '')} {profile_data.get('lastName', '')}".strip(),
                    'company': profile_data.get('company', old_data.get('company', '')),
                    'position': profile_data.get('position', ''),
                    'address1': profile_data.get('address1', old_data.get('address', '')),
                    'address2': profile_data.get('address2', ''),
                    'city': profile_data.get('city', old_data.get('city', '')),
                    'state': profile_data.get('state', old_data.get('state', '')),
                    'country': profile_data.get('country', old_data.get('country', '')),
                    'zip': profile_data.get('zip', old_data.get('zipCode', '')),
                    'homePhone': profile_data.get('homePhone', old_data.get('phone', '')),
                    'workPhone': profile_data.get('workPhone', ''),
                    'cellPhone': profile_data.get('cellPhone', ''),
                    'fax': profile_data.get('fax', ''),
                    'email': profile_data.get('email', old_data.get('email', '')),
                    'website': profile_data.get('website', ''),
                    'username': profile_data.get('username', ''),
                    'password': profile_data.get('password', ''),
                    'creditCardType': profile_data.get('creditCardType', ''),
                    'creditCardNumber': profile_data.get('creditCardNumber', ''),
                    'creditCardExpMonth': profile_data.get('creditCardExpMonth', ''),
                    'creditCardExpYear': profile_data.get('creditCardExpYear', ''),
                    'creditCardCVC': profile_data.get('creditCardCVC', ''),
                    'creditCardName': profile_data.get('creditCardName', ''),
                    'creditCardBank': profile_data.get('creditCardBank', ''),
                    'creditCardServicePhone': profile_data.get('creditCardServicePhone', ''),
                    'sex': profile_data.get('sex', ''),
                    'ssn': profile_data.get('ssn', ''),
                    'driverLicense': profile_data.get('driverLicense', ''),
                    'birthMonth': profile_data.get('birthMonth', ''),
                    'birthDay': profile_data.get('birthDay', ''),
                    'birthYear': profile_data.get('birthYear', ''),
                    'age': profile_data.get('age', ''),
                    'birthPlace': profile_data.get('birthPlace', ''),
                    'income': profile_data.get('income', ''),
                    'customMessage': profile_data.get('customMessage', ''),
                    'comments': profile_data.get('comments', ''),
                    'created_at': existing_profile.get('created_at', time.strftime('%Y-%m-%dT%H:%M:%SZ')),
                    'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')
                }
            else:
                # Update flat format profile
                existing_profile.update({
                    'profileName': profile_data.get('name', existing_profile.get('profileName', '')),
                    'title': profile_data.get('title', existing_profile.get('title', '')),
                    'firstName': profile_data.get('firstName', existing_profile.get('firstName', '')),
                    'middleInitial': profile_data.get('middleInitial', existing_profile.get('middleInitial', '')),
                    'lastName': profile_data.get('lastName', existing_profile.get('lastName', '')),
                    'fullName': f"{profile_data.get('firstName', '')} {profile_data.get('middleInitial', '')} {profile_data.get('lastName', '')}".strip(),
                    'company': profile_data.get('company', existing_profile.get('company', '')),
                    'position': profile_data.get('position', existing_profile.get('position', '')),
                    'address1': profile_data.get('address1', existing_profile.get('address1', '')),
                    'address2': profile_data.get('address2', existing_profile.get('address2', '')),
                    'city': profile_data.get('city', existing_profile.get('city', '')),
                    'state': profile_data.get('state', existing_profile.get('state', '')),
                    'country': profile_data.get('country', existing_profile.get('country', '')),
                    'zip': profile_data.get('zip', existing_profile.get('zip', '')),
                    'homePhone': profile_data.get('homePhone', existing_profile.get('homePhone', '')),
                    'workPhone': profile_data.get('workPhone', existing_profile.get('workPhone', '')),
                    'cellPhone': profile_data.get('cellPhone', existing_profile.get('cellPhone', '')),
                    'fax': profile_data.get('fax', existing_profile.get('fax', '')),
                    'email': profile_data.get('email', existing_profile.get('email', '')),
                    'website': profile_data.get('website', existing_profile.get('website', '')),
                    'username': profile_data.get('username', existing_profile.get('username', '')),
                    'password': profile_data.get('password', existing_profile.get('password', '')),
                    'creditCardType': profile_data.get('creditCardType', existing_profile.get('creditCardType', '')),
                    'creditCardNumber': profile_data.get('creditCardNumber', existing_profile.get('creditCardNumber', '')),
                    'creditCardExpMonth': profile_data.get('creditCardExpMonth', existing_profile.get('creditCardExpMonth', '')),
                    'creditCardExpYear': profile_data.get('creditCardExpYear', existing_profile.get('creditCardExpYear', '')),
                    'creditCardCVC': profile_data.get('creditCardCVC', existing_profile.get('creditCardCVC', '')),
                    'creditCardName': profile_data.get('creditCardName', existing_profile.get('creditCardName', '')),
                    'creditCardBank': profile_data.get('creditCardBank', existing_profile.get('creditCardBank', '')),
                    'creditCardServicePhone': profile_data.get('creditCardServicePhone', existing_profile.get('creditCardServicePhone', '')),
                    'sex': profile_data.get('sex', existing_profile.get('sex', '')),
                    'ssn': profile_data.get('ssn', existing_profile.get('ssn', '')),
                    'driverLicense': profile_data.get('driverLicense', existing_profile.get('driverLicense', '')),
                    'birthMonth': profile_data.get('birthMonth', existing_profile.get('birthMonth', '')),
                    'birthDay': profile_data.get('birthDay', existing_profile.get('birthDay', '')),
                    'birthYear': profile_data.get('birthYear', existing_profile.get('birthYear', '')),
                    'age': profile_data.get('age', existing_profile.get('age', '')),
                    'birthPlace': profile_data.get('birthPlace', existing_profile.get('birthPlace', '')),
                    'income': profile_data.get('income', existing_profile.get('income', '')),
                    'customMessage': profile_data.get('customMessage', existing_profile.get('customMessage', '')),
                    'comments': profile_data.get('comments', existing_profile.get('comments', '')),
                    'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')
                })

            # Save updated profile
            with open(filepath, 'w') as f:
                json.dump(existing_profile, f, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps({'success': True}))
        except Exception as e:
            self.send_error(400, f'Bad request: {str(e)}')

    def handle_delete_profile(self, profile_id):
        """Delete a profile"""
        filepath = os.path.join(self.profiles_dir, f"{profile_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps({'success': True}))
        else:
            self.send_error(404, 'Profile not found')

    def handle_get_settings(self):
        """Get application settings"""
        settings_file = 'settings.json'
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = self.get_default_settings()

        # Only load API keys from .env in development mode (optional)
        # Check for development flag or environment variable
        is_development = os.getenv('ENVIRONMENT') == 'development' or os.path.exists('.env.development')

        # In development, optionally pre-load keys from .env for testing
        # In production, users MUST provide their own keys via UI
        if is_development and os.path.exists('.env'):
            # This is only for development testing
            # Production users will enter their keys through the settings UI
            pass  # Comment out the .env loading for production

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.safe_write_response(json.dumps(settings))

    def handle_save_settings(self, data):
        """Save application settings"""
        try:
            settings = json.loads(data)
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps({'success': True}))
        except Exception as e:
            self.send_error(400, f'Bad request: {str(e)}')

    def handle_save_api_keys(self, data):
        """Save API keys"""
        try:
            api_keys = json.loads(data)

            # Load existing settings or create new
            settings_file = 'settings.json'
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = self.get_default_settings()

            # Update API keys
            settings['apiKeys'] = api_keys

            # Save settings
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)

            # Also save to .env file for backend use
            env_content = []
            if api_keys.get('openai'):
                env_content.append(f"OPENAI_API_KEY={api_keys['openai']}")
            if api_keys.get('anthropic'):
                env_content.append(f"ANTHROPIC_API_KEY={api_keys['anthropic']}")
            if api_keys.get('google'):
                env_content.append(f"GOOGLE_API_KEY={api_keys['google']}")
            if api_keys.get('openrouter'):
                env_content.append(f"OPENROUTER_API_KEY={api_keys['openrouter']}")

            with open('.env', 'w') as f:
                f.write('\n'.join(env_content))

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps({'success': True}))
        except Exception as e:
            self.send_error(400, f'Bad request: {str(e)}')

    def get_default_settings(self):
        """Get default application settings"""
        return {
            'automation': {
                'defaultAiModel': 'claude-3.5-sonnet',
                'defaultMode': 'visible',
                'autoRetry': True,
                'maxRetries': 3
            },
            'browser': {
                'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'pageLoadTimeout': 30,
                'screenshotOnError': True
            },
            'notifications': {
                'email': True,
                'desktop': False,
                'sound': True
            },
            'appearance': {
                'theme': 'auto',
                'sidebarCollapse': True
            },
            'apiKeys': {
                'openai': '',
                'anthropic': '',
                'google': '',
                'openrouter': ''
            }
        }

    def handle_get_saved_urls(self):
        """Get all saved URLs"""
        try:
            urls_file = os.path.join('saved_urls', 'saved_urls.json')
            if os.path.exists(urls_file):
                with open(urls_file, 'r') as f:
                    urls = json.load(f)
            else:
                urls = []

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps(urls))
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')

    def handle_get_saved_url(self, url_id):
        """Get a specific saved URL"""
        try:
            urls_file = os.path.join('saved_urls', 'saved_urls.json')
            if os.path.exists(urls_file):
                with open(urls_file, 'r') as f:
                    urls = json.load(f)

                url = next((u for u in urls if u['id'] == url_id), None)
                if url:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_cors_headers()
                    self.end_headers()
                    self.safe_write_response(json.dumps(url))
                else:
                    self.send_error(404, 'URL not found')
            else:
                self.send_error(404, 'URL not found')
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')

    def handle_create_saved_url(self, data):
        """Create a new saved URL"""
        try:
            url_data = json.loads(data)

            # Generate ID if not provided
            import uuid
            url_id = str(uuid.uuid4())

            # Create URL object
            url_obj = {
                'id': url_id,
                'url': url_data['url'],
                'name': url_data.get('name'),
                'description': url_data.get('description'),
                'group': url_data.get('group'),
                'tags': url_data.get('tags', []),
                'status': url_data.get('status', 'active'),
                'success_rate': None,
                'last_tested': None,
                'test_count': 0,
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')
            }

            # Ensure saved_urls directory exists
            os.makedirs('saved_urls', exist_ok=True)

            # Load existing URLs or create new list
            urls_file = os.path.join('saved_urls', 'saved_urls.json')
            if os.path.exists(urls_file):
                with open(urls_file, 'r') as f:
                    urls = json.load(f)
            else:
                urls = []

            # Add new URL
            urls.append(url_obj)

            # Save back to file
            with open(urls_file, 'w') as f:
                json.dump(urls, f, indent=2)

            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps({'success': True, 'id': url_id}))
        except Exception as e:
            self.send_error(400, f'Bad request: {str(e)}')

    def handle_update_saved_url(self, url_id, data):
        """Update an existing saved URL"""
        try:
            url_data = json.loads(data)

            urls_file = os.path.join('saved_urls', 'saved_urls.json')
            if os.path.exists(urls_file):
                with open(urls_file, 'r') as f:
                    urls = json.load(f)

                # Find and update the URL
                for i, url in enumerate(urls):
                    if url['id'] == url_id:
                        urls[i].update({
                            'url': url_data.get('url', url['url']),
                            'name': url_data.get('name', url.get('name')),
                            'description': url_data.get('description', url.get('description')),
                            'group': url_data.get('group', url.get('group')),
                            'tags': url_data.get('tags', url.get('tags', [])),
                            'status': url_data.get('status', url.get('status', 'active')),
                            'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')
                        })

                        # Save back to file
                        with open(urls_file, 'w') as f:
                            json.dump(urls, f, indent=2)

                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_cors_headers()
                        self.end_headers()
                        self.safe_write_response(json.dumps({'success': True}))
                        return

                self.send_error(404, 'URL not found')
            else:
                self.send_error(404, 'URL not found')
        except Exception as e:
            self.send_error(400, f'Bad request: {str(e)}')

    def handle_delete_saved_url(self, url_id):
        """Delete a saved URL"""
        try:
            urls_file = os.path.join('saved_urls', 'saved_urls.json')
            if os.path.exists(urls_file):
                with open(urls_file, 'r') as f:
                    urls = json.load(f)

                # Filter out the URL to delete
                original_count = len(urls)
                urls = [url for url in urls if url['id'] != url_id]

                if len(urls) < original_count:
                    # Save back to file
                    with open(urls_file, 'w') as f:
                        json.dump(urls, f, indent=2)

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_cors_headers()
                    self.end_headers()
                    self.safe_write_response(json.dumps({'success': True}))
                else:
                    self.send_error(404, 'URL not found')
            else:
                self.send_error(404, 'URL not found')
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')

    def handle_clear_saved_urls(self):
        """Clear all saved URLs"""
        try:
            urls_file = os.path.join('saved_urls', 'saved_urls.json')

            # Write empty array to file
            os.makedirs('saved_urls', exist_ok=True)
            with open(urls_file, 'w') as f:
                json.dump([], f)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps({'success': True}))
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')

    def handle_get_url_groups(self):
        """Get URL groups from saved URLs"""
        try:
            urls_file = os.path.join('saved_urls', 'saved_urls.json')
            groups = []

            if os.path.exists(urls_file):
                with open(urls_file, 'r') as f:
                    urls = json.load(f)

                # Extract unique groups from URLs
                group_names = set()
                for url in urls:
                    if url.get('group'):
                        group_names.add(url['group'])

                # Create group objects
                for group_name in sorted(group_names):
                    group_urls = [url for url in urls if url.get('group') == group_name]
                    groups.append({
                        'name': group_name,
                        'count': len(group_urls),
                        'urls': group_urls
                    })

                # Add ungrouped URLs
                ungrouped_urls = [url for url in urls if not url.get('group')]
                if ungrouped_urls:
                    groups.append({
                        'name': 'Ungrouped',
                        'count': len(ungrouped_urls),
                        'urls': ungrouped_urls
                    })

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.safe_write_response(json.dumps(groups))
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')

    def serve_static_file(self, path):
        """Serve static files"""
        # Default to index.html for root path
        if path == '/':
            path = '/web/index.html'
        elif path == '/profiles':
            path = '/web/profiles.html'
        elif path == '/settings':
            path = '/web/settings.html'
        elif path == '/automation':
            path = '/web/automation.html'
        elif path == '/recorder':
            path = '/web/recorder.html'
        elif path == '/account':
            path = '/web/account.html'
        elif path == '/saved-pages':
            path = '/web/saved_pages.html'
        elif path == '/saved-urls':
            path = '/web/saved_urls.html'
        elif path == '/previous-orders':
            path = '/web/previous_orders.html'

        # Remove leading slash for file path
        file_path = path[1:] if path.startswith('/') else path

        # Security check - prevent directory traversal
        file_path = os.path.normpath(file_path)
        if '..' in file_path:
            self.send_error(403, 'Forbidden')
            return

        # Check if file exists
        if os.path.exists(file_path) and os.path.isfile(file_path):
            # Get content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

            # Send file
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_cors_headers()
            self.end_headers()

            with open(file_path, 'rb') as f:
                self.safe_write_response(f.read())
        else:
            self.send_error(404, 'File not found')

    def handle_websocket_upgrade(self):
        """Handle WebSocket upgrade request"""
        # Check for WebSocket headers
        if (self.headers.get('Connection', '').lower() != 'upgrade' or
            self.headers.get('Upgrade', '').lower() != 'websocket'):
            self.send_error(400, 'Bad Request')
            return

        # Get WebSocket key
        websocket_key = self.headers.get('Sec-WebSocket-Key')
        if not websocket_key:
            self.send_error(400, 'Missing Sec-WebSocket-Key')
            return

        # Calculate accept key
        accept_key = base64.b64encode(
            hashlib.sha1((websocket_key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()
        ).decode()

        # Send upgrade response
        self.send_response(101, 'Switching Protocols')
        self.send_header('Upgrade', 'websocket')
        self.send_header('Connection', 'Upgrade')
        self.send_header('Sec-WebSocket-Accept', accept_key)
        self.end_headers()

        # Keep the connection alive by not returning immediately
        # The connection is now established and ready for messages
        self.handle_websocket_connection()

    def handle_websocket_connection(self):
        """Handle WebSocket connection after upgrade"""
        try:
            # Send initial connection message
            self.send_websocket_message(json.dumps({
                'type': 'connection',
                'status': 'connected',
                'message': 'WebSocket connection established'
            }))

            # Keep connection alive with a simple approach
            # Just wait and let the client maintain the connection
            while True:
                try:
                    # Small delay to prevent busy waiting
                    time.sleep(10)

                    # Send periodic status update
                    self.send_websocket_message(json.dumps({
                        'type': 'status',
                        'timestamp': time.time(),
                        'server': 'FormAI Enhanced'
                    }))

                except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                    # Client disconnected
                    break
                except Exception:
                    break

        except Exception:
            pass

    def send_websocket_message(self, message):
        """Send a WebSocket message"""
        try:
            if isinstance(message, str):
                message = message.encode('utf-8')

            # Create WebSocket frame
            frame = bytearray()
            frame.append(0x81)  # FIN + text frame

            msg_len = len(message)
            if msg_len < 126:
                frame.append(msg_len)
            elif msg_len < 65536:
                frame.append(126)
                frame.extend(struct.pack('>H', msg_len))
            else:
                frame.append(127)
                frame.extend(struct.pack('>Q', msg_len))

            frame.extend(message)
            self.wfile.write(frame)
            self.wfile.flush()
        except:
            pass

    def safe_write_response(self, data):
        """Safely write response data, handling connection errors"""
        try:
            if isinstance(data, str):
                self.wfile.write(data.encode())
            else:
                self.wfile.write(data)
        except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
            # Client disconnected, ignore the error
            pass

    def log_message(self, format, *args):
        """Suppress logs for cleaner output"""
        pass

def main():
    print("\n" + "="*50)
    print("    FormAI Enhanced Server - Full Features")
    print("="*50 + "\n")

    PORT = 5511
    print(f"FormAI Enhanced Server is running at:")
    print(f"   http://localhost:{PORT}")
    print(f"\nFull API support enabled!")
    print(f"Serving profiles from: ./profiles")
    print("\nPress Ctrl+C to stop\n")

    httpd = HTTPServer(('localhost', PORT), FormAIEnhancedHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nFormAI Enhanced Server stopped")

if __name__ == "__main__":
    main()