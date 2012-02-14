# -*- coding: utf-8 -*-
import os
import random
import simplejson as json
import string
import time

from httplib2 import Http
from PIL import Image
from pymongo import DESCENDING
from pymongo.objectid import ObjectId
from urllib import urlencode

from flask import (abort, Flask, jsonify, redirect,
     render_template, request, session, url_for)

import settings

from helper import *
from snappy import Snappy

app = Flask(__name__)
app.secret_key = settings.SESSION_SECRET

h = Http()
snappy = Snappy()
PHOTO_THUMB = 250, 250
PHOTO_MEDIUM = 992, 600


@app.route('/', methods=['GET'])
def main():
    """Default landing page"""
    try:
        snapshot = snappy.db.photos.find().sort("created_at",
                DESCENDING).limit(1)[0]
    except IndexError:
        snapshot = []
    return render_template('index.html',
                            snapshot=snapshot,
                            photo_count=snappy.get_photo_count())
                        

@app.route('/get_snapshot/<page>/<nav>', methods=['GET'])
def get_snapshot(page=1, nav='next'):
    """Get the latest snapshot from pagination/navigation"""
    snapshot = snappy.get_recent(page=page, nav=nav)
    return jsonify({'snapshot':
            {'image_medium': snapshot['image_medium'],
             'id': str(ObjectId(snapshot['_id']))}})


@app.route('/tag/<tag>', methods=['GET'])
def get_first_tag(tag=None):
    """Get the latest snapshot matching this tag."""
    snapshot = snappy.get_recent_tag(tag=tag)
    return render_template('tag.html',
                            snapshot=snapshot,
                            photo_count=snappy.get_photo_count(tag=tag),
                            tag=tag)


@app.route('/tag/<tag>/<page>/<nav>', methods=['GET'])
def get_tag(tag=None, page=1, nav='next'):
    """Get the latest snapshot matching this tag."""
    snapshot = snappy.get_recent_tag(tag=tag, page=page, nav=nav)
    return jsonify({'snapshot':
            {'image_medium': snapshot['image_medium'],
             'id': str(ObjectId(snapshot['_id']))}})


@app.route('/favorite/<id>', methods=['GET'])
@authenticated
def favorite(id=None):
    """Favorite/Unfavorite a snapshot."""
    return jsonify({'snapshot':
                   {'favorited': snappy.favorited(id,
                            session['snapshots_token'])}})


@app.route('/add_comment', methods=['POST'])
@authenticated
def add_comment():
    """Add a new comment to a snapshot."""
    comment = snappy.add_comment(request.form['id'],
                                 session['snapshots_token'],
                                 request.form['description'])
    if comment:
        print comment
        return jsonify({'comment':
                   {'description': comment['description'],
                    'id': str(ObjectId(comment['_id']))}})
    else:
        return jsonify({'error':'comment cannot be blank'})


@app.route('/delete_comment/<id>', methods=['GET'])
@authenticated
def delete_comment(id=None):
    """Delete a comment."""
    comment = snappy.delete_comment(id, session['snapshots_token'])
    return jsonify({'message':'comment deleted'})
                   

@app.route('/snapshots/<id>', methods=['GET'])
@authenticated
def snapshots():
    """User snapshots."""
    return render_template('snapshots.html')


@app.route('/set_email', methods=['POST'])
def set_email():
    """Verify via BrowserID and upon success, set
    the email for the user unless it already
    exists and return the token.
    """
    bid_fields = {'assertion': request.form['bid_assertion'],
                  'audience': settings.DOMAIN}
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    h.disable_ssl_certificate_validation=True
    resp, content = h.request('https://browserid.org/verify',
                              'POST',
                              body=urlencode(bid_fields),
                              headers=headers)
    bid_data = json.loads(content)
    if bid_data['status'] == 'okay' and bid_data['email']:
        # authentication verified, now get/create the
        # snappy email token
        snappy.get_or_create_email(bid_data['email'])
        session['snapshots_token'] = snappy.token
        session['snapshots_email'] = bid_data['email']
    return redirect(url_for('profile'))


@app.route('/profile', methods=['GET', 'POST'])
@authenticated
@csrf_protect
def profile():
    """View and update profile information."""
    user = snappy.get_or_create_email(session['snapshots_email'])
    if request.method == 'POST':
        snappy.update_profile(session['snapshots_email'],
                              full_name=request.form['full_name'],
                              bio=request.form['bio'],
                              website=request.form['website'])
        return redirect(url_for('profile'))
    else:
        return render_template('profile.html',
                                user=user,
                                gravatar=gravatar(session['snapshots_email'],
                                                  size=80))


@app.route('/dashboard', methods=['GET', 'POST'])
@authenticated
@csrf_protect
def dashboard():
    """View dashboard."""
    user = snappy.get_or_create_email(session['snapshots_email'])
    snapshots = snappy.get_latest_snapshots(user['token'])
    return render_template('dashboard.html',
                            user=user,
                            snapshots=snapshots,
                            gravatar=gravatar(session['snapshots_email'],
                                              size=80))


@app.route('/user/<id>', methods=['GET'])
def user_snapshot_first(id=None):
    """User's first snapshot."""
    user = snappy.get_user_by_id(id)
    snapshot = snappy.get_recent_by_user(user['token'])
    return render_template('user.html',
                            user=user,
                            snapshot=snapshot,
                            photo_count=snappy.get_photo_count_by_user(user['token']))


@app.route('/user/<id>/<page>/<nav>', methods=['GET'])
def user_snapshots(id=None, page=1, nav='next'):
    """User's snapshots."""
    user = snappy.get_user_by_id(id)
    snapshot = snappy.get_recent_by_user(user['token'], page=page, nav=nav)
    print(snapshot)
    return jsonify({'snapshot':
            {'image_medium': snapshot['image_medium'],
             'id': str(ObjectId(snapshot['_id']))}})


@app.route('/upload', methods=['GET', 'POST'])
@authenticated
@csrf_protect
def upload():
    """Upload a photo and save two versions - the original, medium
    and the thumb.
    """
    if request.method == 'POST' and request.files['photo']:
        filename = str(int(time.time()))
        request.files['photo'].save(os.path.join('tmp/', filename))

        thumb = Image.open(os.path.join('tmp/', filename))
        thumb.thumbnail(PHOTO_THUMB, Image.BICUBIC)
        thumb.save('tmp/' + filename + '_thumb', 'JPEG')

        medium = Image.open(os.path.join('tmp/', filename))
        medium.thumbnail(PHOTO_MEDIUM, Image.BICUBIC)
        medium.save('tmp/' + filename + '_medium', 'JPEG')

        large = Image.open(os.path.join('tmp/', filename))
        large.save('tmp/' + filename + '_original', 'JPEG')
        snapshot = snappy.upload(request.form['description'],
                                 filename,
                                 session.get('snapshots_token'))
        return redirect(url_for('snapshot', id=snapshot['_id']))
    else:
        return render_template('upload.html')


@app.route('/snapshot/<id>', methods=['GET'])
def snapshot(id=None):
    """Your snapshot."""
    snapshot = snappy.get_image(id)
    user = snappy.get_user_by_token(snapshot['token'])
    if session['snapshots_email']:
        return render_template('snapshot.html', snapshot=snapshot,
                                gravatar=gravatar(snappy.get_email(
                                        snapshot['token'])),
                                user=user,
                                favorited=snappy.is_favorited(id,
                                        session['snapshots_token']),
                                comments=snappy.get_comments(id))
    else:
        return render_template('snapshot.html', snapshot=snapshot,
                                gravatar=gravatar(snappy.get_email(
                                        snapshot['token'])),
                                user=user,
                                comments=snappy.get_comments(id))


@app.route('/snapshot/edit/<id>', methods=['GET', 'POST'])
@authenticated
@csrf_protect
def edit(id=None):
    """Edit or update an existing snapshot."""
    snapshot = snappy.get_image_by_user(id, session['snapshots_token'])

    if not snapshot:
        return redirect(url_for('main'))
    else:
        if request.method == 'POST':
            snappy.update_description(id, request.form['description'])
            return redirect(url_for('snapshot', id=snapshot['_id']))
        else:
            return render_template('edit.html', snapshot=snapshot)


@app.route('/snapshot/delete/<id>', methods=['GET'])
@authenticated
def delete(id=None):
    """Delete an existing snapshot."""
    snappy.delete_image(id, session['snapshots_token'])
    return redirect(url_for('main'))


@app.route('/logout', methods=['GET'])
def logout():
    """Log the user out"""
    session['snapshots_email'] = None
    session['snapshots_token'] = None
    return redirect(url_for('main'))


def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = ''.join(
                random.choice(string.ascii_lowercase + string.digits) for x in range(30))

    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token


if __name__ == '__main__':
    app.debug = settings.DEBUG
    app.env = 'dev'
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
