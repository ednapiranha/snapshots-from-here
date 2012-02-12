import base64
import os
import random
import time

from auto_tagify import AutoTagify
from boto.s3.key import Key
from PIL import Image
from pymongo import DESCENDING
from pymongo.objectid import ObjectId

import settings

CONTENT_TYPE = 'image/jpeg'
ATAG = AutoTagify()
ATAG.link = "/tag"


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
        """Upload the image to the user's account. Also, autotag the
        description.
        """
        image_full_path = os.path.join('tmp/', filename + '_original')
        image_full_path_medium = os.path.join('tmp/', filename + '_medium')

        aws_key = Key(settings.BUCKET)
        aws_key.key = filename + '_original.jpg'
        aws_key.set_contents_from_filename(image_full_path,
                                           headers={'Content-Type': CONTENT_TYPE})
        image_full_path_original = '%s%s_original.jpg' % (settings.IMAGE_URL,
                                                          filename)
        
        aws_key.key = filename + '_medium.jpg'
        aws_key.set_contents_from_filename(image_full_path_medium,
                                           headers={'Content-Type': CONTENT_TYPE})
        image_full_path_medium = '%s%s_medium.jpg' % (settings.IMAGE_URL,
                                                      filename)

        ATAG.text = description
        tagged_description = ATAG.generate()
        
        self.db.photos.update({"image_filename":filename},
                              {"$set":{"description":description,
                                       "tagged_description":tagged_description,
                                       "tags":ATAG.tag_list(),
                                       "image_original":image_full_path_original,
                                       "image_medium":image_full_path_medium,
                                       "token":sender_token,
                                       "created_at":int(time.time())}},
                                        upsert=True)

        ATAG.text = ''
        # self.db.photos.ensureIndex({"image_filename.tags": 1})
        return self.db.photos.find_one({"image_filename":filename})

    def update_description(self, image_id, description):
        """Update the description for the image."""
        ATAG.text = description
        tagged_description = ATAG.generate()

        self.db.photos.update({"_id":ObjectId(image_id)},
                              {"$set":{"description":description,
                                       "tagged_description":tagged_description,
                                       "tags":ATAG.tag_list()}})
        ATAG.text = ''

    def get_recent(self, page=0, nav='next'):
        """Get all recently uploaded images. Navigation defaults at the next
        image created (descending). If navigation is set to 'prev', we go in the
        reverse direction.
        """
        photos = self.db.photos.find().sort("created_at", DESCENDING)
        page = self._set_page(photos, page, nav)

        try:
            return photos.skip(page*1).limit(1)[0]
        except IndexError:
            return self.db.photos.find().sort("created_at").limit(1)[0]

    def get_recent_tag(self, tag=None, page=0, nav='next'):
        """Get all recently uploaded images matching this tag. Navigation
        defaults at the next image created (descending). If navigation is set to
        'prev', we go in the reverse direction.
        """
        photos = self.db.photos.find({"tags":tag}).sort("created_at", DESCENDING)
        page = self._set_page(photos, page, nav)

        try:
            return photos.skip(page*1).limit(1)[0]
        except IndexError:
            return self.db.photos.find().sort("created_at").limit(1)[0]

    def get_photo_count(self, tag=None):
        """Get the total number of photos. If a tag is specified,
        get the total number with that tag.
        """
        if tag:
            return self.db.photos.find({"tags":tag}).count()
        else:
            return self.db.photos.count()        

    def get_image(self, image_id):
        """Return the image matching the given id."""
        return self.db.photos.find_one({"_id":ObjectId(image_id)})

    def get_image_by_user(self, image_id, sender_token):
        """Return an image matching the given id and user."""
        return self.db.photos.find_one({"_id":ObjectId(image_id),
                                        "token":sender_token})
    
    def delete_image(self, image_id, sender_token):
        """Delete the image matching the given id and user."""
        photo = self.db.photos.find_one({"_id":ObjectId(image_id),
                                         "token":sender_token})
        settings.BUCKET.delete_keys((photo['image_filename'] + '_medium.jpg',
                                     photo['image_filename'] + '_original.jpg'))
        self.db.photos.remove({"_id":ObjectId(image_id)})

    def _set_page(self, photos, page, nav):
        """Set the page and nav values."""
        page = int(page)
        if nav == 'next' and photos.count() > 1:
            if page > photos.count():
                page = photos.count()
        elif nav == 'prev':
            if page < 0:
                page = 0
        else:
            page = 0
        return int(page)
