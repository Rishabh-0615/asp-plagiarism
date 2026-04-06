"""Cloudinary Service for downloading submission files"""
import cloudinary
import cloudinary.api
import requests
import logging
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

logger = logging.getLogger(__name__)

class CloudinaryService:
    def __init__(self):
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET
        )

    def download_file(self, file_url: str, local_path: str = None) -> str:
        """
        Download file from Cloudinary URL
        
        Args:
            file_url (str): Cloudinary file URL or public_id
            local_path (str): Optional local path to save file
            
        Returns:
            str: Path to downloaded file or URL
        """
        try:
            # If it's a Cloudinary public_id, construct the URL
            if not file_url.startswith('http'):
                file_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload/{file_url}"

            response = requests.get(file_url, timeout=30)
            response.raise_for_status()

            if local_path:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"File downloaded to {local_path}")
                return local_path

            return file_url

        except Exception as e:
            logger.error(f"Error downloading from Cloudinary: {str(e)}")
            raise

    def get_file_resource_info(self, public_id: str) -> dict:
        """
        Get file metadata from Cloudinary
        
        Args:
            public_id (str): Cloudinary public_id
            
        Returns:
            dict: File metadata
        """
        try:
            resource = cloudinary.api.resource(public_id)
            return resource
        except Exception as e:
            logger.error(f"Error getting resource info: {str(e)}")
            raise
