import os
import io
import json
import unittest
import tempfile
import shutil
from app import app, load_config, save_config, get_safe_filepath, get_shared_files

class LocalFileDistributorTestCase(unittest.TestCase):

    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Create a temporary directory to act as the shared directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Create some test files in the temporary directory
        self.test_file_name1 = "test_file_1.txt"
        self.test_file_path1 = os.path.join(self.temp_dir, self.test_file_name1)
        with open(self.test_file_path1, 'w') as f:
            f.write("Hello world! This is a test file.")
            
        # Create a nested subfolder
        self.sub_dir_name = "documents"
        self.sub_dir_path = os.path.join(self.temp_dir, self.sub_dir_name)
        os.makedirs(self.sub_dir_path)
        
        self.test_file_name2 = "manual.pdf"
        self.test_file_path2 = os.path.join(self.sub_dir_path, self.test_file_name2)
        with open(self.test_file_path2, 'w') as f:
            f.write("This is a mock PDF file content.")
            
        # Create a dummy config file
        self.original_config_exists = os.path.exists('config.json')
        if self.original_config_exists:
            with open('config.json', 'r') as f:
                self.original_config = json.load(f)
        else:
            self.original_config = None
            
        # Write test configuration
        self.test_token = "testtoken123"
        self.test_config = {
            "shared_folder": self.temp_dir,
            "password_enabled": False,
            "password": "",
            "host_token": self.test_token
        }
        save_config(self.test_config)

    def tearDown(self):
        # Clean up files and directories
        shutil.rmtree(self.temp_dir)
        
        # Restore original config
        if self.original_config:
            save_config(self.original_config)
        elif os.path.exists('config.json'):
            os.remove('config.json')

    def test_safe_path_resolution(self):
        """Verifies that only files under the shared directory are resolved, and traversals are blocked."""
        # Valid path
        valid_rel = "test_file_1.txt"
        resolved = get_safe_filepath(self.temp_dir, valid_rel)
        self.assertEqual(resolved, os.path.realpath(self.test_file_path1))
        
        # Valid nested path
        valid_nested = "documents/manual.pdf"
        resolved_nested = get_safe_filepath(self.temp_dir, valid_nested)
        self.assertEqual(resolved_nested, os.path.realpath(self.test_file_path2))
        
        # Path traversal attempt outside shared directory
        traversal_path = "../config.json"
        with self.assertRaises(PermissionError):
            get_safe_filepath(self.temp_dir, traversal_path)
            
        # Attempting directory as file
        dir_path = "documents"
        with self.assertRaises(ValueError):
            get_safe_filepath(self.temp_dir, dir_path)

    def test_get_shared_files(self):
        """Checks if files list metadata contains all files recursively."""
        files = get_shared_files(self.temp_dir)
        self.assertEqual(len(files), 2)
        
        # Extract relative paths
        rel_paths = [f['rel_path'] for f in files]
        self.assertIn("test_file_1.txt", rel_paths)
        self.assertIn("documents/manual.pdf", rel_paths)
        
        # Check metadata structures
        file_meta = next(f for f in files if f['name'] == 'test_file_1.txt')
        self.assertEqual(file_meta['size_bytes'], len("Hello world! This is a test file."))
        self.assertTrue('size_str' in file_meta)
        self.assertTrue('date_added' in file_meta)

    def test_index_route(self):
        """Verifies dashboard loading without auth required."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Local File Distributor', response.data)
        
    def test_files_list_api(self):
        """Tests reading shared files list from endpoint."""
        response = self.client.get('/api/files')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        
        self.assertEqual(data['count'], 2)
        self.assertEqual(len(data['files']), 2)
        self.assertTrue('total_size_str' in data)

    def test_download_endpoint(self):
        """Tests that client can download a file and it increments download counter."""
        # Initial list check
        res1 = self.client.get('/api/files')
        data1 = json.loads(res1.data.decode('utf-8'))
        file_meta = next(f for f in data1['files'] if f['name'] == 'test_file_1.txt')
        self.assertEqual(file_meta['download_count'], 0)
        
        # Download file
        dl_res = self.client.get('/download/test_file_1.txt')
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.data, b"Hello world! This is a test file.")
        
        # Post download count check
        res2 = self.client.get('/api/files')
        data2 = json.loads(res2.data.decode('utf-8'))
        file_meta_after = next(f for f in data2['files'] if f['name'] == 'test_file_1.txt')
        self.assertEqual(file_meta_after['download_count'], 1)

    def test_blocked_directory_traversal_on_download(self):
        """Ensures traversal file download is blocked."""
        response = self.client.get('/download/../config.json')
        self.assertIn(response.status_code, (400, 403, 404))

    def test_host_api_unauthorized(self):
        """Checks that clients cannot view or change host config without token."""
        client_env = {'REMOTE_ADDR': '192.168.1.50'}
        # View config
        resp_get = self.client.get('/api/host/config', environ_overrides=client_env)
        self.assertEqual(resp_get.status_code, 403)
        
        # Edit config
        resp_post = self.client.post('/api/host/config', json={"password_enabled": True}, environ_overrides=client_env)
        self.assertEqual(resp_post.status_code, 403)
        
        # Browse directory
        resp_browse = self.client.get('/api/host/browse', environ_overrides=client_env)
        self.assertEqual(resp_browse.status_code, 403)

    def test_host_api_authorized(self):
        """Checks host configuration retrieval/editing with token."""
        headers = {'X-Host-Token': self.test_token}
        
        # Read configs
        resp_get = self.client.get('/api/host/config', headers=headers)
        self.assertEqual(resp_get.status_code, 200)
        config_data = json.loads(resp_get.data.decode('utf-8'))
        self.assertEqual(config_data['shared_folder'], self.temp_dir)
        self.assertEqual(config_data['password_enabled'], False)
        
        # Modify configs (set password)
        resp_post = self.client.post('/api/host/config', json={
            "password_enabled": True,
            "password": "secureshare"
        }, headers=headers)
        self.assertEqual(resp_post.status_code, 200)
        
        # Check config updated
        updated_config = load_config()
        self.assertTrue(updated_config['password_enabled'])
        self.assertEqual(updated_config['password'], 'secureshare')

    def test_password_authentication(self):
        """Validates that password restricts access and successful auth grants access."""
        client_env = {'REMOTE_ADDR': '192.168.1.50'}
        # Restrict portal
        self.test_config["password_enabled"] = True
        self.test_config["password"] = "schoolroom"
        save_config(self.test_config)
        
        # Verify index shows password authentication is needed
        resp_index = self.client.get('/', environ_overrides=client_env)
        self.assertEqual(resp_index.status_code, 200)
        self.assertIn(b'Password Required', resp_index.data)
        
        # Verify APIs fail with 401 Unauthorized
        resp_api = self.client.get('/api/files', environ_overrides=client_env)
        self.assertEqual(resp_api.status_code, 401)
        
        # Authenticate with wrong password
        resp_auth_fail = self.client.post('/api/auth', json={"password": "wrongpassword"}, environ_overrides=client_env)
        self.assertEqual(resp_auth_fail.status_code, 401)
        
        # Authenticate with correct password
        resp_auth_ok = self.client.post('/api/auth', json={"password": "schoolroom"}, environ_overrides=client_env)
        self.assertEqual(resp_auth_ok.status_code, 200)
        
        # Extract set client cookie
        self.assertEqual(resp_auth_ok.headers.get('Set-Cookie').split(';')[0], 'client_auth=schoolroom')

    def test_host_page_unauthorized(self):
        """Verifies `/host` blocks unauthorized remote client access."""
        client_env = {'REMOTE_ADDR': '192.168.1.50'}
        resp = self.client.get('/host', environ_overrides=client_env)
        self.assertEqual(resp.status_code, 403)

    def test_host_page_authorized(self):
        """Verifies `/host` permits local loopback or token authenticated access."""
        # 1. Localhost auto-auth
        resp_local = self.client.get('/host')
        self.assertEqual(resp_local.status_code, 200)

        # 2. Token header auth
        client_env = {'REMOTE_ADDR': '192.168.1.50'}
        headers = {'X-Host-Token': self.test_token}
        resp_token = self.client.get('/host', headers=headers, environ_overrides=client_env)
        self.assertEqual(resp_token.status_code, 200)

    def test_host_upload_and_delete(self):
        """Verifies uploading files writes to disk, and deleting removes them securely."""
        headers = {'X-Host-Token': self.test_token}
        client_env = {'REMOTE_ADDR': '192.168.1.50'}
        
        # Test file binary stream payload
        file_payload = (io.BytesIO(b"Dynamic uploaded file test data."), "uploaded_test.txt")
        data = {
            'files': file_payload
        }
        
        # 1. Post upload request
        resp_up = self.client.post('/api/host/upload', 
                                  data=data, 
                                  content_type='multipart/form-data', 
                                  headers=headers, 
                                  environ_overrides=client_env)
        self.assertEqual(resp_up.status_code, 200)
        
        # Verify file presence on disk
        target_path = os.path.join(self.temp_dir, "uploaded_test.txt")
        self.assertTrue(os.path.exists(target_path))
        with open(target_path, 'r') as f:
            self.assertEqual(f.read(), "Dynamic uploaded file test data.")
            
        # Verify file registered on API files list
        resp_files = self.client.get('/api/files')
        data_files = json.loads(resp_files.data.decode('utf-8'))
        file_names = [f['name'] for f in data_files['files']]
        self.assertIn("uploaded_test.txt", file_names)
        
        # 2. Post delete request
        resp_del = self.client.post('/api/host/delete', 
                                    json={"rel_path": "uploaded_test.txt"}, 
                                    headers=headers, 
                                    environ_overrides=client_env)
        self.assertEqual(resp_del.status_code, 200)
        
        # Verify file deleted from disk
        self.assertFalse(os.path.exists(target_path))
        
        # Verify file unregistered from API files list
        resp_files_after = self.client.get('/api/files')
        data_files_after = json.loads(resp_files_after.data.decode('utf-8'))
        file_names_after = [f['name'] for f in data_files_after['files']]
        self.assertNotIn("uploaded_test.txt", file_names_after)

    def test_host_upload_duplicate_rename(self):
        """Verifies duplicate uploads automatically rename instead of overwriting."""
        headers = {'X-Host-Token': self.test_token}
        client_env = {'REMOTE_ADDR': '192.168.1.50'}
        
        # test_file_1.txt already exists (from setUp)
        file_payload = (io.BytesIO(b"Duplicate name content stream."), "test_file_1.txt")
        data = {
            'files': file_payload
        }
        
        # Upload
        resp_up = self.client.post('/api/host/upload', 
                                  data=data, 
                                  content_type='multipart/form-data', 
                                  headers=headers, 
                                  environ_overrides=client_env)
        self.assertEqual(resp_up.status_code, 200)
        
        # Verify it was renamed to test_file_1_1.txt
        resp_data = json.loads(resp_up.data.decode('utf-8'))
        self.assertEqual(resp_data['uploaded'][0], "test_file_1_1.txt")
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "test_file_1_1.txt")))

if __name__ == '__main__':
    unittest.main()
