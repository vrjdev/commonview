define(['pixel_group', 'helpers'], function(PixelGroup, helpers) {
    return function(picture, groupSize) {
        this.groups = [];
        this.groupIndex = {};
        this.next_max_tag_id = undefined;
        this.globalDiff = 255;
        this.tagName = '';

        var canvas = document.createElement('canvas'),
            ctx = canvas.getContext('2d');

        canvas.width = groupSize;
        canvas.height = groupSize;

        for (var i = 0; i < picture.pixels.length; i++) {
            var x = picture.pixels[i].x,
                y = picture.pixels[i].y,
                color = picture.pixels[i].color,
                gX = Math.floor(x/groupSize),
                gY = Math.floor(y/groupSize);

            if (this.groupIndex[gX] === undefined)
                this.groupIndex[gX] = {};
            var pixelGroup = this.groupIndex[gX][gY];

            if (pixelGroup === undefined) {
                pixelGroup = new PixelGroup(groupSize, gX, gY);
                this.groups.push(pixelGroup);
                this.groupIndex[gX][gY] = pixelGroup;
            }

            pixelGroup.addPixel(x % groupSize, y % groupSize, color);
        }


        this.toHash = function() {
            var trueGroups = {};
            for (var i = 0; i < this.groups.length; i++) {
                var groupHash = this.groups[i].toHash();
                if (groupHash !== undefined) {
                    if (trueGroups[groupHash.x] === undefined)
                        trueGroups[groupHash.x] = {};
                    trueGroups[groupHash.x][groupHash.y] = groupHash;
                }
            }
            return {
                groups: trueGroups,
                globalDiff: this.globalDiff,
                tagName: this.tagName,
                next_max_tag_id: this.next_max_tag_id
            }
        }


        this.fromHash = function(params) {
            // params: data, onComplete, onInit, onProgress

            var data = params.data;
            this.next_max_tag_id = data.next_max_tag_id;
            this.globalDiff = data.globalDiff;
            this.tagName = data.tagName;

            var counter = 0,
                maxCounter;

            function decreaseCounter() {
                counter--;

                if (counter > 0 && counter % 10 == 0 && params.onProgress !== undefined)
                    params.onProgress(100 * (maxCounter - counter) / maxCounter);

                if (counter == 0 && params.onComplete !== undefined)
                    params.onComplete();
            }

            for (var x in data.groups)
                for (var y in data.groups[x]) {
                    counter++;

                    var g = this.groupIndex[x][y];
                    g.loading = true;
                    g.fromHash(data.groups[x][y]);
                    this.addPhoto(g.image, false,
                        function(group) {
                            return function() {
                                //console.log('Old photo loaded');
                                group.loading = false;
                                decreaseCounter();
                            }
                        } (g),
                        function(group) {
                            return function() {
                                console.log('Old photo not found');
                                group.loading = false;
                                group.image = undefined;
                                decreaseCounter();
                            }
                        } (g)
                    );
                }

            maxCounter = counter;
            if (params.onInit !== undefined) params.onInit();
        }


        this.addPhoto = function(colorImage, findPlace, success, error) {
            var palette = this;
            helpers.loadImgByUrl({
                url: colorImage.imageUrl,
                success: function(img) {
                    ctx.drawImage(img, 0, 0, img.width, img.height, 0, 0, groupSize, groupSize);
                    var imgData = ctx.getImageData(0, 0, groupSize, groupSize),
                        colors = helpers.getImgDataColors(imgData);
                    
                    colorImage.color = colors;

                    if (findPlace)
                        palette._findPlace(colorImage);

                    palette.globalDiff = palette.groups.reduce(function (a, b) {return a + b.diff; }, 0) / palette.groups.length;

                    success();
                },
                error: error,
            });
        }


        this._findPlace = function(colorImage) {
            var freeMedia = colorImage;
            
            for (var i = 0; i < this.groups.length; i++) {
                var g = this.groups[i];
                if (g.loading)
                    continue;

                var diff = g.calcDiff(freeMedia.color);

                if (g.diff > diff) {
                    if (g.image !== undefined) {
                        var tmp = g.image;
                        g.image = freeMedia;
                        g.diff = diff;
                        freeMedia = tmp;
                    }
                    else {
                        g.image = freeMedia;
                        g.diff = diff;
                        break;
                    }
                }
            }
        }
    }
})