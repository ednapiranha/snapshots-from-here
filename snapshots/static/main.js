$(function() {
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
    $('body').keydown(function(event) {
        var self = $('.home img');
        var nav = 'next';
        var photo_count = parseInt($(this).find('.photo').data('photo-count'), 10);

        // left or prev
        if(event.which == 37) {
            page--;
            if(page < 1) {
                page = 1;
            }
            nav = 'prev';
        // right or next
        } else if(event.which == 39) {
            page++;
            if(page > photo_count) {
                page = photo_count;
            }
            nav = 'next';
        }

        $.getJSON('/get_snapshot/'+page+'/'+nav, function(data) {
            self.attr('src', data['snapshot']['image_medium']);
        });
    });

});