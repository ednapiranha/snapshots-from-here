$(function() {
    "use strict";
    var page = 0;

    // BrowserID login
    $('#login').click(function() {
        navigator.id.getVerifiedEmail(function(assertion) {
            if(assertion) {
                $('form input').val(assertion);
                $('form').submit();
            }
        });
    });

    // Pagination/Navigation functionality for left/right keys
    $('body.home').keydown(function(event) {
        var self = $('.home img');
        var nav = 'next';
        var photo_count = parseInt($(this).find('.photo').data('photo-count'), 10);

        // left or prev
        if(event.which === 37) {
            page--;
            if(page < 0) {
                page = 0;
            }
            nav = 'prev';
        // right or next
        } else if(event.which === 39) {
            page++;
            if(page > photo_count) {
                page = photo_count;
            }
            nav = 'next';
        }

        $.getJSON(self.data('url')+page+'/'+nav, function(data) {
            self.attr('src', data.snapshot.image_medium);
            self.closest('a').attr('href', '/snapshot/'+data.snapshot.id);
        });
    });

});