import urllib2, cStringIO
from PIL import Image

class ImageHelper:
    @staticmethod
    def get_image_color(url, size):
        try:
            f = cStringIO.StringIO(urllib2.urlopen(url).read())
        except urllib2.HTTPError:
            return None

        img = Image.open(f)
        img.thumbnail((size, size))
        return reduce(lambda a, b: a + b, img.getdata(), ())


    @staticmethod
    def add_color_to_media(m, size):
        img = m['image']
        img.thumbnail((size, size))

        return {
            'media': m['media'],
            'colors': reduce(lambda a, b: a + b, img.getdata(), ())
        }


    @staticmethod
    def download_img(m):
        try:
            f = cStringIO.StringIO(urllib2.urlopen(m.get_thumbnail_url()).read())
        except urllib2.HTTPError:
            return None

        return {
            'media': m,
            'image': Image.open(f)
        }