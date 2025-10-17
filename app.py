from flask import Flask, jsonify, send_file, request, make_response
from flask_cors import CORS
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import io
import json
import tempfile
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add models directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'models'))

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:5173",
    "http://localhost:3000", 
    "https://frontend-ten-eta-28.vercel.app",
    "https://*.vercel.app"
]) # Enable CORS for React frontend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDriveService:
    def __init__(self):
        self.drive = None
        self.initialize_drive()
    
    def initialize_drive(self):
        """Initialize Google Drive connection"""
        try:
            logger.info("Starting Google Drive initialization...")
            
            # Debug: Check environment variables
            client_secrets_env = os.environ.get('CLIENT_SECRETS_JSON')
            credentials_env = os.environ.get('CREDENTIALS_JSON')
            flask_env = os.environ.get('FLASK_ENV')
            
            logger.info(f"Environment check:")
            logger.info(f"- FLASK_ENV: {flask_env}")
            logger.info(f"- CLIENT_SECRETS_JSON present: {bool(client_secrets_env)}")
            logger.info(f"- CREDENTIALS_JSON present: {bool(credentials_env)}")
            
            gauth = GoogleAuth()
            
            # Check if we have client secrets in environment variable
            if client_secrets_env:
                logger.info("Creating client_secrets.json from environment variable")
                # Create client_secrets.json from environment variable
                with open('client_secrets.json', 'w') as f:
                    if isinstance(client_secrets_env, str):
                        # If it's a JSON string, parse it first
                        try:
                            client_secrets_data = json.loads(client_secrets_env)
                            json.dump(client_secrets_data, f)
                        except json.JSONDecodeError:
                            # If it's not valid JSON, write it as is
                            f.write(client_secrets_env)
                    else:
                        json.dump(client_secrets_env, f)
                logger.info("Created client_secrets.json from environment variable")
            else:
                logger.warning("CLIENT_SECRETS_JSON environment variable not found")
            
            # Check if we have credentials in environment variable
            if credentials_env:
                logger.info("Creating credentials.json from environment variable")
                # Create credentials.json from environment variable
                with open('credentials.json', 'w') as f:
                    if isinstance(credentials_env, str):
                        try:
                            credentials_data = json.loads(credentials_env)
                            json.dump(credentials_data, f)
                        except json.JSONDecodeError:
                            f.write(credentials_env)
                    else:
                        json.dump(credentials_env, f)
                logger.info("Created credentials.json from environment variable")
            else:
                logger.warning("CREDENTIALS_JSON environment variable not found")
            
            # Try to load saved credentials
            gauth.LoadCredentialsFile("credentials.json")
            
            if gauth.credentials is None:
                # Authenticate if credentials are not available
                logger.info("No credentials found. Starting authentication flow...")
                # For production, we'll need to handle this differently
                if os.environ.get('FLASK_ENV') == 'production':
                    logger.error("Cannot perform interactive authentication in production")
                    raise Exception("Production deployment requires pre-authenticated credentials")
                else:
                    gauth.LocalWebserverAuth()
            elif gauth.access_token_expired:
                # Refresh credentials if expired
                logger.info("Credentials expired. Refreshing...")
                gauth.Refresh()
            else:
                # Initialize the saved credentials
                gauth.Authorize()
                
            # Save the current credentials to file
            gauth.SaveCredentialsFile("credentials.json")
            
            self.drive = GoogleDrive(gauth)
            logger.info("Google Drive initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            logger.error("Please ensure you have:")
            logger.error("1. Created client_secrets.json with your Google API credentials")
            logger.error("2. Enabled Google Drive API in Google Cloud Console")
            logger.error("3. Set up OAuth 2.0 Client ID credentials")
            raise e
    
    def search_bat_folder(self, server_num, client_num, bat_id):
        """
        Search for folder with pattern: SERVER{server_num}_CLIENT{client_num}_{bat_id}
        """
        folder_name = f"SERVER{server_num}_CLIENT{client_num}_{bat_id}"
        
        try:
            # Search for folders with the exact name
            query = f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            file_list = self.drive.ListFile({'q': query}).GetList()
            
            if file_list:
                logger.info(f"Found folder: {folder_name}")
                return file_list[0]  # Return first matching folder
            else:
                logger.warning(f"No folder found with name: {folder_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching for folder {folder_name}: {e}")
            return None
    
    def get_folder_files(self, folder_id):
        """Get all files in a specific folder"""
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            file_list = self.drive.ListFile({'q': query}).GetList()
            
            files_info = []
            for file in file_list:
                files_info.append({
                    'id': file['id'],
                    'name': file['title'],
                    'mimeType': file['mimeType'],
                    'downloadUrl': file.get('downloadUrl', ''),
                    'modifiedDate': file.get('modifiedDate', '')
                })
            
            return files_info
            
        except Exception as e:
            logger.error(f"Error getting files from folder {folder_id}: {e}")
            return []
    
    def list_all_folders(self):
        """List all folders in Google Drive to debug"""
        try:
            query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
            file_list = self.drive.ListFile({'q': query}).GetList()
            
            folders = []
            for folder in file_list:
                folders.append({
                    'id': folder['id'],
                    'name': folder['title'],
                    'modifiedDate': folder.get('modifiedDate', '')
                })
            
            logger.info(f"Found {len(folders)} folders in Google Drive")
            return folders
            
        except Exception as e:
            logger.error(f"Error listing folders: {e}")
            return []
    
    def list_all_items_detailed(self):
        """List all items in Google Drive with detailed info for debugging"""
        try:
            # Get all items in root
            query = "'root' in parents and trashed=false"
            file_list = self.drive.ListFile({'q': query}).GetList()
            
            items = []
            for item in file_list:
                items.append({
                    'id': item['id'],
                    'title': item['title'],
                    'mimeType': item.get('mimeType', 'unknown'),
                    'createdDate': item.get('createdDate', 'unknown'),
                    'modifiedDate': item.get('modifiedDate', 'unknown'),
                    'parents': item.get('parents', [])
                })
            
            logger.info(f"Found {len(items)} items in Google Drive root")
            return items
            
        except Exception as e:
            logger.error(f"Error listing all items: {e}")
            return []

    def download_and_store_locally(self, file_id, file_name, local_folder):
        """Download a file from Google Drive and store locally"""
        try:
            # Create local storage directory if it doesn't exist
            os.makedirs(local_folder, exist_ok=True)
            
            file = self.drive.CreateFile({'id': file_id})
            local_path = os.path.join(local_folder, file_name)
            
            # Download the file
            file.GetContentFile(local_path)
            logger.info(f"Downloaded {file_name} to {local_path}")
            
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return None

# Initialize Google Drive service
drive_service = GoogleDriveService()

@app.route('/api/debug/folders')
def list_all_folders():
    """Debug endpoint to list all folders in Google Drive"""
    try:
        folders = drive_service.list_all_folders()
        return jsonify({
            'success': True,
            'total_folders': len(folders),
            'folders': folders
        })
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/debug/all-items')
def list_all_items():
    """Debug endpoint to list all items in Google Drive with detailed info"""
    try:
        items = drive_service.list_all_items_detailed()
        return jsonify({
            'success': True,
            'total_items': len(items),
            'items': items
        })
    except Exception as e:
        logger.error(f"Error listing all items: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/debug/download/<bat_id>')
def debug_download_files(bat_id):
    """Debug endpoint to download and store files locally"""
    try:
        # Extract server and client info from query parameters
        server_num = request.args.get('server', '1')
        client_num = request.args.get('client', '1')
        
        # Extract numeric part from BAT ID
        numeric_bat_id = bat_id.replace('BAT', '')
        
        # Search for the folder
        folder = drive_service.search_bat_folder(server_num, client_num, numeric_bat_id)
        
        if not folder:
            return jsonify({
                'success': False,
                'message': f'Folder not found for SERVER{server_num}_CLIENT{client_num}_{numeric_bat_id}'
            }), 404
        
        # Get files in the folder
        files = drive_service.get_folder_files(folder['id'])
        
        # Create local storage folder
        local_folder = f"downloads/SERVER{server_num}_CLIENT{client_num}_{numeric_bat_id}"
        downloaded_files = []
        
        # Download all files
        for file in files:
            local_path = drive_service.download_and_store_locally(
                file['id'], 
                file['name'], 
                local_folder
            )
            if local_path:
                downloaded_files.append({
                    'original_name': file['name'],
                    'local_path': local_path,
                    'file_id': file['id']
                })
        
        return jsonify({
            'success': True,
            'folder_name': folder['title'],
            'total_files': len(files),
            'downloaded_files': downloaded_files,
            'local_folder': local_folder
        })
        
    except Exception as e:
        logger.error(f"Error in debug download for BAT {bat_id}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/bat/<bat_id>/files')
def get_bat_files(bat_id):
    """Get all files for a specific BAT ID"""
    try:
        # Extract server and client info from query parameters
        server_num = request.args.get('server', '1')
        client_num = request.args.get('client', '1')
        
        # Extract numeric part from BAT ID (e.g., BAT121 -> 121)
        numeric_bat_id = bat_id.replace('BAT', '')
        
        # Search for the folder
        folder = drive_service.search_bat_folder(server_num, client_num, numeric_bat_id)
        
        if not folder:
            return jsonify({
                'success': False,
                'message': f'Folder not found for SERVER{server_num}_CLIENT{client_num}_{numeric_bat_id}'
            }), 404
        
        # Get files in the folder
        files = drive_service.get_folder_files(folder['id'])
        
        # Organize files by type
        organized_files = {
            'spectrogram': None,
            'camera': None,
            'sensor': None,
            'audio': None,
            'other': []
        }
        
        for file in files:
            file_name_lower = file['name'].lower()
            # Handle both "spectrogram" and "spectogram" (with missing 'r')
            if ('spectrogram' in file_name_lower or 'spectogram' in file_name_lower) and file_name_lower.endswith('.jpg'):
                organized_files['spectrogram'] = file
            elif 'camera' in file_name_lower and file_name_lower.endswith('.jpg'):
                organized_files['camera'] = file
            elif 'sensor' in file_name_lower and file_name_lower.endswith('.txt'):
                organized_files['sensor'] = file
            elif 'audio' in file_name_lower and file_name_lower.endswith('.wav'):
                organized_files['audio'] = file
            else:
                organized_files['other'].append(file)
        
        return jsonify({
            'success': True,
            'folder_name': folder['title'],
            'folder_id': folder['id'],
            'files': organized_files
        })
        
    except Exception as e:
        logger.error(f"Error getting files for BAT {bat_id}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/file/<file_id>')
def download_file_endpoint(file_id):
    """Download a specific file from Google Drive"""
    try:
        file_name = request.args.get('name', 'file')
        
        # Download the file to temp location
        file = drive_service.drive.CreateFile({'id': file_id})
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}")
        file.GetContentFile(temp_file.name)
        
        # Determine mime type based on file extension
        mime_type = 'application/octet-stream'
        if file_name.lower().endswith('.jpg') or file_name.lower().endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif file_name.lower().endswith('.png'):
            mime_type = 'image/png'
        elif file_name.lower().endswith('.txt'):
            mime_type = 'text/plain'
        
        return send_file(
            temp_file.name,
            mimetype=mime_type,
            as_attachment=False,
            download_name=file_name
        )
        
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/debug/upload-sensor/<bat_id>')
def upload_sensor_file(bat_id):
    """Debug endpoint to upload a sample sensor.txt file to Google Drive"""
    try:
        # Extract server and client info from query parameters
        server_num = request.args.get('server', '1')
        client_num = request.args.get('client', '1')
        
        folder_name = f"SERVER{server_num}_CLIENT{client_num}_{bat_id}"
        
        # Find the folder
        folder = drive_service.search_bat_folder(server_num, client_num, bat_id)
        if not folder:
            return jsonify({
                'success': False,
                'message': f'Folder not found: {folder_name}'
            }), 404
        
        # Read the sample sensor file
        sample_file_path = os.path.join(os.path.dirname(__file__), 'sample_sensor.txt')
        if not os.path.exists(sample_file_path):
            return jsonify({
                'success': False,
                'message': 'Sample sensor file not found'
            }), 404
        
        # Upload the file to Google Drive
        file_metadata = {
            'title': 'Sensor.txt',
            'parents': [{'id': folder['id']}]
        }
        
        file = drive_service.drive.CreateFile(file_metadata)
        file.SetContentFile(sample_file_path)
        file.Upload()
        
        logger.info(f"Uploaded Sensor.txt to folder {folder_name}")
        
        return jsonify({
            'success': True,
            'message': f'Sensor.txt uploaded to {folder_name}',
            'file_id': file['id'],
            'folder_id': folder['id']
        })
        
    except Exception as e:
        logger.error(f"Error uploading sensor file: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Backend service is running',
        'timestamp': datetime.now().isoformat()
    })

# Mock species data for testing without Google Drive/Model
MOCK_SPECIES_DATA = {
    '825': {'species': 'Hipposideros_speoris', 'confidence': 92.5},
    '826': {'species': 'Pipistrellus_coromandra', 'confidence': 88.3},
    '827': {'species': 'Rhinolophus_rouxii', 'confidence': 95.1},
    '828': {'species': 'Taphozous_melanopogon', 'confidence': 85.7},
    '829': {'species': 'Megaderma_lyra', 'confidence': 91.2},
    '830': {'species': 'Unknown_species', 'confidence': 45.3},
}

@app.route('/api/predict/<bat_id>', methods=['GET'])
def predict_species(bat_id):
    """
    Predict bat species from spectrogram image.
    For local testing, returns mock data. For production, would use ML model.
    
    Query params:
    - server: server number (optional)
    - client: client number (optional)
    - mock: set to 'true' to use mock data (default is true for testing)
    """
    try:
        # Get query parameters
        server = request.args.get('server', '1')
        client = request.args.get('client', '1')
        use_mock = request.args.get('mock', 'true').lower() == 'true'
        
        logger.info(f"Predicting species for BAT {bat_id} (Server {server}, Client {client}) - Mock: {use_mock}")
        
        # Check if we have mock data for this BAT
        if use_mock or bat_id in MOCK_SPECIES_DATA:
            mock_prediction = MOCK_SPECIES_DATA.get(bat_id, {
                'species': 'Unknown_species',
                'confidence': 50.0
            })
            logger.info(f"Using mock prediction: {mock_prediction['species']} ({mock_prediction['confidence']}%)")
            
            return jsonify({
                'success': True,
                'species': mock_prediction['species'],
                'confidence': mock_prediction['confidence'],
                'bat_id': bat_id,
                'mode': 'mock'
            })
        
        # Real prediction with Google Drive + Model (if mock is disabled)
        logger.warning("Mock mode disabled but BAT ID not in mock data - returning error")
        return jsonify({
            'success': False,
            'message': f'BAT {bat_id} not found in mock data and mock mode is disabled',
            'species': 'Unknown species',
            'confidence': 0
        }), 404
    
    except Exception as e:
        logger.error(f"Error predicting species: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e),
            'species': 'Unknown species',
            'confidence': 0
        }), 500

@app.route('/api/species-image/<species_name>', methods=['GET', 'OPTIONS'])
def get_species_image(species_name):
    """
    Get species image from local bat_species folder.
    Maps species name to corresponding image file.
    
    Example: /api/species-image/Hipposideros_speoris
    """
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 204
    try:
        # Get the backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        species_dir = os.path.join(backend_dir, 'bat_species')
        
        logger.info(f"Looking for species image: {species_name}")
        logger.info(f"Species directory: {species_dir}")
        
        if not os.path.exists(species_dir):
            logger.error(f"Species directory not found: {species_dir}")
            return jsonify({
                'success': False,
                'message': 'Species directory not found'
            }), 500
        
        # Try to find image with species name (with various extensions)
        possible_names = [
            f"{species_name}.jpg",
            f"{species_name}.jpeg",
            f"{species_name}.png",
            f"{species_name}.JPG",
            f"{species_name}.JPEG",
            f"{species_name}.PNG"
        ]
        
        image_path = None
        for name in possible_names:
            path = os.path.join(species_dir, name)
            if os.path.exists(path):
                image_path = path
                logger.info(f"Found species image: {path}")
                break
        
        # Fallback to Unknown_species if not found
        if not image_path:
            logger.warning(f"Species image not found for {species_name}, using Unknown_species")
            unknown_path = os.path.join(species_dir, 'Unknown_species.jpg')
            if os.path.exists(unknown_path):
                image_path = unknown_path
            else:
                return jsonify({
                    'success': False,
                    'message': 'Species image not found'
                }), 404
        
        # Send the image file with proper headers
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        response = make_response(image_data)
        response.headers['Content-Type'] = 'image/jpeg'
        response.headers['Content-Disposition'] = f'inline; filename="{os.path.basename(image_path)}"'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    
    except Exception as e:
        logger.error(f"Error retrieving species image: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
