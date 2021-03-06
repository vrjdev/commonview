from flask import Flask, render_template, request, redirect, url_for, current_app, session, jsonify, g, send_file
import json
from instagram import client
from picprocess.image_helper import ImageHelper
from picprocess.pixels import Pixels
from picprocess.palette import Palette
import os
from .env_settings import load_env
from flask.ext.scss import Scss
from .db.engine import init_db, get_db
from .db.models import *
import cStringIO
import re


app = Flask(__name__, instance_relative_config=True)
app.config.from_object('web.default_settings')
load_env(app)
app.config.from_pyfile('application.cfg', silent=True)

Scss(app)

init_db(app)


def get_unauthenticated_api(**kwargs):
    return client.InstagramAPI(client_id=current_app.config['INSTA_ID'],
                               client_secret=current_app.config['INSTA_SECRET'],
                               redirect_uri=url_for('insta_code', _external=True, **kwargs))


@app.before_request
def before_request():
    db = get_db()
    db.connect()

    if 'user_id' in session:
        g.authorized = True
        # load from db if not /img or /resize
        g.user = User.get(User.id == session['user_id'])
    else:
        g.authorized = False
        g.user = None


@app.after_request
def after_request(response):
    get_db().close()
    return response


@app.route('/login')
def login():
    return redirect(get_unauthenticated_api().get_authorize_url())


@app.route('/logout')
def logout():
    if g.authorized:
        del session['user_id']
    return redirect(url_for('index'))


@app.route('/insta_code')
def insta_code():
    code = request.args.get('code')
    try:
        access_token, user_info = get_unauthenticated_api().exchange_code_for_access_token(code)

        try:
            user = User.get(User.insta_id == user_info[u'id'])
            if user.insta_name != user_info[u'username']: user.insta_name = user_info[u'username']
            if user.access_token != access_token: user.access_token = access_token
            user.save()
        except User.DoesNotExist:
            user = User.create(insta_id=user_info[u'id'],
                               insta_name=user_info[u'username'],
                               access_token=access_token)

        session['user_id'] = user.id

        return redirect(url_for('index'))
    except Exception as e:
        print e
        return 'error'


@app.route('/')
def index():
    if g.authorized:
        can_upload = g.user.pictures.count() < current_app.config['MAX_UPLOADS'] 
        return render_template('pictures.html',
            can_upload=can_upload,
            max_count=current_app.config['MAX_UPLOADS'],
            max_size=current_app.config['MAX_CONTENT_LENGTH'])
    else:
        return render_template('index.html')


@app.route('/pic/<id>', methods=['GET', 'DELETE'])
def render(id):
    picture = Picture.get(Picture.id == id)

    if request.method == 'GET':
        pixels = Pixels()
        pixels.get_pixels_from_img(picture)

        if not g.authorized or picture.user.id != g.user.id:
            return render_template('showpicture.html',
                    picture=picture,
                    pixels=json.dumps(pixels.to_hash()),
                    group_size=current_app.config['GROUP_SIZE'],
                    export_pic_size=current_app.config['EXPORT_GROUP_SIZE'],
                    palette=json.dumps(Palette.load_from_db(picture)),
                )
        else:
            return render_template('render.html',
                    picture=picture,
                    pixels=json.dumps(pixels.to_hash()),
                    access_token=g.user.access_token,
                    group_size=current_app.config['GROUP_SIZE'],
                    export_pic_size=current_app.config['EXPORT_GROUP_SIZE'],
                    palette=json.dumps(Palette.load_from_db(picture)),
                )
    else:
        Palette.remove_from_db(picture)
        return jsonify(result='ok')



@app.route('/pic/<id>/preview')
def preview(id):
    try:
        picture = Picture.get(Picture.id==id)
    except Picture.DoesNotExist:
        return 'Not found', 404

    return send_file(cStringIO.StringIO(picture.image), mimetype='image/jpeg')


@app.route('/pic/<id>/export')
def export(id):
    try:
        picture = Picture.get(Picture.id==id)
    except Picture.DoesNotExist:
        return 'Not found', 404

    result = ImageHelper.compile_image(picture)
    return send_file(result, mimetype='image/png')


@app.route('/palette/<id>', methods=['POST'])
def palette(id):
    try:
        picture = Picture.get(Picture.id==id)
    except Picture.DoesNotExist:
        return 'Not found', 404

    if not g.authorized or picture.user.id != g.user.id:
        return 'error', 500

    if Palette.save_to_db(picture, request.form['palette']):
        return jsonify(result='ok')
    else:
        return jsonify(error='wrong data'), 500


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@app.route('/upload', methods=['POST'])
def upload():
    if not g.authorized or g.user.pictures.count() >= current_app.config['MAX_UPLOADS']:
        return 'error', 500

    f = request.files['pic']
    if f and allowed_file(f.filename):
        with get_db().atomic() as txn:
            pic, size = ImageHelper.resize(f, current_app.config['IMAGE_WIDTH'])
            picture = Picture.create(
                user=g.user,
                width=size[0],
                height=size[1],
                image=pic.getvalue())
        return jsonify(result='ok', url=url_for('render', _external=True, id=picture.id))
    else:
        return jsonify(result='error'), 500


@app.route('/img/<id>')
def img(id):
    try:
        picture = Picture.get(Picture.id==id)
    except Picture.DoesNotExist:
        return 'Not found', 404

    if not g.authorized or picture.user.id != g.user.id: return 'error', 500
    
    insta_img = request.args.get('insta_img') # check root!
    insta_id = request.args.get('insta_id')
    insta_url = request.args.get('insta_url').split('/')[-2] # remain just id
    insta_user = request.args.get('insta_user')

    insta_url_re = re.compile(current_app.config['ALLOWED_INSTA_URL'])
    if not insta_url_re.match(insta_url):
        return 'Wrong url', 500

    free_fragments = picture.fragments.where(Fragment.x == None)
    overcome = free_fragments.count() - current_app.config['MAX_CACHED_PHOTOS']

    if overcome >= 0:
        to_remove = [f.id for f in free_fragments.limit(overcome + 1)]
        Fragment.delete().where(Fragment.id << to_remove, Fragment.x == None).execute()

    result = ImageHelper.get_new_image(insta_img)

    if result != None:
        fragment = Fragment.create(picture=picture,
                                   insta_img=insta_img,
                                   insta_id=insta_id,
                                   insta_url=insta_url,
                                   insta_user=insta_user,
                                   high_pic=result[0],
                                   low_pic=result[1])

        return jsonify(fragment.to_hash())
    else:
        return 'Cannot download image', 500



if __name__ == '__main__':
    app.run()