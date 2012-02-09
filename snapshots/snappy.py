import base64
import os
import random
import time

from boto.s3.key import Key
from PIL import Image
from pymongo import DESCENDING
from pymongo.objectid import ObjectId

import settings

CONTENT_TYPE = 'image/png'


class Snappy(object):
    """All the snapshot functionality"""
    def __init__(self):
        self.token = ''
        self.env = 'dev'
        self.db = settings.DATABASE

    def set_environment(self, env='dev'):
        if env == 'test':
            self.env = env
            self.db = settings.TEST_DATABASE
    
    def get_or_create_email(self, email):
        """Find the email address in the system
        or create it if it doesn't exist.
        """
        email = email.lower().strip()
        if not self.db.users.find_one({"email":email}):
            self.db.users.update({"email":email},
                                 {"$set":{"token":self._generate_token(email)}},
                                   upsert=True)
        emailer = self.db.users.find_one({"email":email})
        self.token = emailer['token']
        return emailer

    def _generate_token(self, email):
        """Generate a token based on the timestamp and the user's
        email address.
        """
        random_int = str(random.randrange(100, 10000))
        token_string = '%s%s%s' % (random_int,
                                   email,
                                   str(int(time.time())))
        return base64.b64encode(token_string)

    def upload(self, description, filename, sender_token):
        """Upload the image to the user's account."""
        image_full_path = os.path.join('tmp/', filename + '_original')
        image_full_path_thumb = os.path.join('tmp/', filename + '_thumb')

        aws_key = Key(settings.BUCKET)
        aws_key.key = filename + '_original.png'
        aws_key.set_contents_from_filename(image_full_path,
                                           headers={'Content-Type': CONTENT_TYPE})
        image_full_path_original = '%s%s_original.png' % (settings.IMAGE_URL,
                                                          filename)

        aws_key.key = filename + '_thumb.png'
        aws_key.set_contents_from_filename(image_full_path_thumb,
                                           headers={'Content-Type': CONTENT_TYPE})
        image_full_path_thumb = '%s%s_thumb.png' % (settings.IMAGE_URL, filename)
        
        self.db.photos.update({"image_filename":filename},
                                {"$set":{"description":description,
                                         "image_original":image_full_path_original,
                                         "image_thumb":image_full_path_thumb,
                                         "token":sender_token,
                                         "created_at":int(time.time())}},
                                          upsert=True) 
        return image_full_path
        
    def get_recent(self):
        """Get all recently uploaded images."""
        return self.db.photos.find().sort("created_at", DESCENDING)                    
