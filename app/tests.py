import unittest
import os

class TestBasicFunctionality(unittest.TestCase):
    def test_app_import(self):
        try:
            from app import app
            self.assertTrue(True)
        except ImportError:
            self.assertTrue(False, "No se pudo importar la app")
    
    def test_config_files_exist(self):
        self.assertTrue(os.path.exists('requirements.txt'))
        self.assertTrue(os.path.exists('Dockerfile'))

if __name__ == '__main__':
    unittest.main()
