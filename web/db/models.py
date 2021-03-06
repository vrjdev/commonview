from peewee import *
from .engine import get_db
from flask import current_app
import os


class User(Model):
    insta_id = CharField()
    insta_name = CharField()
    access_token = CharField()

    class Meta:
        database = get_db()


class Picture(Model):
    user = ForeignKeyField(User, related_name='pictures')
    width = IntegerField()
    height = IntegerField()
    tag = CharField(null=True)
    next_tag_id = CharField(null=True)
    global_diff = DoubleField(null=True)
    updated = DateTimeField(null=True)
    image = BlobField()

    def diff_percentage(self):
        return round(100 * (255 - self.global_diff) / 255, 1) if self.global_diff != None else 0

    class Meta:
        database = get_db()


class Fragment(Model):
    picture = ForeignKeyField(Picture, related_name='fragments')
    x = IntegerField(null=True)
    y = IntegerField(null=True)
    diff = IntegerField(null=True)
    insta_id = CharField()
    insta_img = CharField()
    insta_url = CharField()
    insta_user = CharField()
    low_pic = BlobField()
    high_pic = BlobField()

    def to_hash(self):
        return {
            'id': self.id,
            #'x': self.x,
            #'y': self.y,
            'diff': self.diff,
            'instaId': self.insta_id,
            'instaImg': self.insta_img,
            'instaUrl': self.insta_url,
            'instaUser': self.insta_user,
            'lowPic': [ord(c) for c in self.low_pic]
        }


    class Meta:
        database = get_db()
