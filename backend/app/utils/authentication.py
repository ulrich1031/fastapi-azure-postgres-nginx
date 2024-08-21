import os
import jwt
import json
from app.config import get_settings

class AuthenticationUtil:
    """
    Utility functions for processing files
    """
    def __init__(self):
        self.settings = get_settings()
        
    def jwt_encode(self, payload: dict) -> str:
        """
        Encode the payload to create a JWT with secret key.

        Parameters:

            payload : Content to be encoded
        
        Returns:
        
            str : The encoded result token
        """
        token = jwt.encode(payload, self.settings.DJANGO_SERVER_JWT_SECRET_KEY, algorithm='HS256')
        return token