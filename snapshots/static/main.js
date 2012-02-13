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

    // Favorite/Unfavorite a snapshot
    $('.photo').on('click', '.actions .like', function(event) {
        var self = $(this);

        event.preventDefault();

        $.getJSON(self.attr('href'), function(data) {
            if(data.snapshot.favorited) {
                self.removeClass('favorited');
                self.text('Favorite');
            } else {
                self.addClass('favorited');
                self.text('Unfavorite');
            }
        });
    });

    // Add a comment
    $('.comments').on('click', 'form', function(event) {
        var self = $(this);

        event.preventDefault();
        
        $.post(self.attr('action'), self.serialize(), function(data) {
           var comment = $('<p></p>');
           var delete_link = $('<a href="/delete_comment/'+data.comment.id+'" class="delete">delete</a>');
           comment.text(data.comment.description);
           comment.append(delete_link);
           self.after(comment);
           self.closest('form').find('input[name="description"]').clear();
        });
    });

    // Delete a comment
    $('.photo').on('click', '.comments .delete', function(event) {
        var self = $(this);

        event.preventDefault();

        $.getJSON(self.attr('href'), function(data) {
           self.parent().remove(); 
        });
    });
});