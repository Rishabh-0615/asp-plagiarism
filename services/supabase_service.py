"""Supabase Service for persisting AI detection into existing submissions table"""
import logging
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_TABLE

try:
    from supabase import create_client
except ImportError:
    create_client = None

logger = logging.getLogger(__name__)


SUBMISSIONS_TABLE = "submissions"

class SupabaseService:
    def __init__(self):
        if not create_client:
            logger.warning("Supabase client not installed")
            self.client = None
        else:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                logger.error(f"Error initializing Supabase: {str(e)}")
                self.client = None

    def save_ai_detection(self, submission_id: str, ai_detection_data: dict) -> dict:
        """
        Save AI detection result into existing submissions row
        
        Args:
            submission_id (str): Unique submission ID
            ai_detection_data (dict): AI detection result
                {
                    "ai_score": 85.5,
                    "human_score": 14.5,
                    "confidence": 0.95,
                    "label": "AI-generated"
                }
        
        Returns:
            dict: Updated submission record or error
        """
        if not self.client:
            logger.error("Supabase client not available")
            return {"error": "Supabase not initialized"}

        try:
            ai_percent = float(ai_detection_data.get("ai_score", 0) or 0)
            label = ai_detection_data.get("label", "")
            updates = {
                "ai_generated_percent": round(ai_percent, 2),
                # Reuse existing column to mark analysis outcome while keeping schema unchanged.
                "content_type": "AI_GENERATED" if label == "AI-generated" else "HUMAN_WRITTEN"
            }

            response = self.client.table(SUBMISSIONS_TABLE).update(updates).eq(
                "id", submission_id
            ).execute()

            if not response.data:
                return {"error": f"Submission not found: {submission_id}"}

            logger.info(f"AI detection updated for submission {submission_id}")
            return response.data[0]

        except Exception as e:
            logger.error(f"Error saving to Supabase: {str(e)}")
            return {"error": str(e)}

    def get_detection_by_submission(self, submission_id: str) -> dict:
        """
        Retrieve AI detection result from existing submissions row
        
        Args:
            submission_id (str): Submission ID
            
        Returns:
            dict: Detection result or empty dict
        """
        if not self.client:
            return {}

        try:
            response = self.client.table(SUBMISSIONS_TABLE).select(
                "id, ai_generated_percent, content_type, file_url, file_name, submitted_at"
            ).eq(
                "id", submission_id
            ).execute()

            return response.data[0] if response.data else {}

        except Exception as e:
            logger.error(f"Error retrieving from Supabase: {str(e)}")
            return {}

    def update_detection(self, submission_id: str, updates: dict) -> dict:
        """
        Update AI detection columns in submissions table
        
        Args:
            submission_id (str): Submission ID
            updates (dict): Fields to update
            
        Returns:
            dict: Updated record or error
        """
        if not self.client:
            return {"error": "Supabase not initialized"}

        try:
            response = self.client.table(SUBMISSIONS_TABLE).update(updates).eq(
                "id", submission_id
            ).execute()

            logger.info(f"AI detection updated for submission {submission_id}")
            return response.data[0] if response.data else updates

        except Exception as e:
            logger.error(f"Error updating Supabase record: {str(e)}")
            return {"error": str(e)}

    def delete_detection(self, submission_id: str) -> dict:
        """
        Clear AI detection value in submissions table
        
        Args:
            submission_id (str): Submission ID
            
        Returns:
            dict: Deletion status
        """
        if not self.client:
            return {"error": "Supabase not initialized"}

        try:
            response = self.client.table(SUBMISSIONS_TABLE).update({
                "ai_generated_percent": None,
                "content_type": "STUDENT_SUBMISSION"
            }).eq("id", submission_id).execute()

            logger.info(f"AI detection cleared for submission {submission_id}")
            return response.data[0] if response.data else {"status": "cleared"}

        except Exception as e:
            logger.error(f"Error deleting from Supabase: {str(e)}")
            return {"error": str(e)}
