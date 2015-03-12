define(['libs/d3'], function(d3) {
    function setBackground(d) {
        if (d.image !== undefined)
            return 'url(' + d.image.imageUrl + ')';
        else
            return 'none';
    }

    function setHref(d) {
        if (d.image !== undefined)
            return d.image.link;
        else
            return '#';
    }

    function drawPalette(palette) {
        var photos = d3.select('#mainPhoto').selectAll('.miniPhoto')
                .data(palette.groups, function(d) {
                    return d.x + '/' + d.y;
                })
                .attr('href', setHref);

        photos.select('div')
            .style('background-image', setBackground);

        photos.enter().append('a')
            .classed('miniPhoto', true)
            .attr('href', setHref)
            .attr('target', '_blank')
            .append('div')
                .attr('row', function(d) { return d.y; })
                .attr('column', function(d) { return d.x; })
                .style('background-image', setBackground);

        photos.exit().remove();

        updateAccuracy(palette);
    }

    function updateAccuracy(palette) {
        var v = palette.globalDiff ? (100 * (255 - palette.globalDiff) / 255) : 0;
        console.log(v);
        d3.selectAll('.accuracyPercentage')
            .text(v.toFixed(1) + '%')
            .style('color', 'hsl(' + (120 * v / 100) + ', 50%, 60%)');
    }

    function showLoading(percentage) {
        d3.select('#loadingPercentage').text(percentage.toFixed(1) + '%');
    }

    return {
        drawPalette: drawPalette,
        showLoading: showLoading,
    }
});