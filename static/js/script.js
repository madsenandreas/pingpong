let white_count = 0;
let black_count = 0;
let chosen_index = null;
const whiteSideNames = [
    "Fellowship",            // Lord of the Rings
    "Jedi",                 // Star Wars
    "Federation",           // Star Trek
    "Dumbledore's Army",    // Harry Potter
    "The Doctor",           // Doctor Who
    "X-Men",                // X-Men
    "Zion",                 // Matrix
    "Serenity",             // Firefly
    "Winchester",           // Supernatural
];

const blackSideNames = [
    "Mordor",               // Lord of the Rings
    "Sith",                 // Star Wars
    "Klingon",              // Star Trek
    "Death Eaters",         // Harry Potter
    "Dalek",                // Doctor Who
    "Brotherhood",          // X-Men
    "Machine",              // Matrix
    "Alliance",             // Firefly
    "Demons",                // Supernatural
];

function updateTeamNames() {
    let new_index;
    do {
        new_index = Math.floor(Math.random() * whiteSideNames.length);
    } while (new_index === chosen_index);
    
    chosen_index = new_index;
    const randomWhiteName = whiteSideNames[chosen_index];
    const randomBlackName = blackSideNames[chosen_index];
    $('#white_side_name').text(randomWhiteName);
    $('#black_side_name').text(randomBlackName);
}

function checkWinner() {
    if (white_count === 0 && black_count === 0) {
        // Reset panels to original state
        $('.white-half').animate({width: '50%'}, 500);
        $('.black-half').animate({width: '50%'}, 500);
        $('.cake').addClass('hidden');
        $('.cake').css('bottom', '-100%');
        updateTeamNames(); // Update names when game resets
    } else if (white_count >= 11) {
        if (black_count === 0) {
            $('.black-half').animate({width: '0%'}, 250);
            $('.white-half').animate({width: '100%'}, 250);
            $('.cake').css('bottom', '-100%')
            $('.cake').css('right', '45%')
            $('.cake').removeClass('hidden');
            $('.cake').animate({bottom: '-10%'}, 1000);

            confetti({
                particleCount: 150,
                spread: 150,
                origin: { y: 0.6 },
                colors: ['#000000', '#202020', '#404040']
            });
            
        } else {
            $('.black-half').animate({width: '0%'}, 500);
            $('.white-half').animate({width: '100%'}, 500);
            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 },
                colors: ['#000000', '#202020', '#404040']
            });
        }
    } else if (black_count >= 11) {
        if (white_count === 0) {
            $('.white-half').animate({width: '0%'}, 250);
            $('.black-half').animate({width: '100%'}, 250);
            $('.cake').css('bottom', '-100%')
            $('.cake').css('left', '45%')
            $('.cake').removeClass('hidden');
            $('.cake').animate({bottom: '-10%'}, 1000);
            // Add black confetti
            confetti({
                particleCount: 150,
                spread: 100,
                origin: { y: 0.6 },
                colors: ['#ffffff', '#f0f0f0', '#e0e0e0']
            });
        } else {
            $('.white-half').animate({width: '0%'}, 500);
            $('.black-half').animate({width: '100%'}, 500);
            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 },
                colors: ['#ffffff', '#f0f0f0', '#e0e0e0']
            });
        }
    }
}

function updateInstructions() {
    if (white_count > 0 || black_count > 0) {
        $('.instructions').fadeOut(500);
    } else {
        $('.instructions').fadeIn(500);
    }
}

$(document).ready(function() {
    updateTeamNames(); // Update names when DOM loads
    
    $.getJSON('/isDebug', function(data) {
        if (data.debug) {
            $('#button_white').removeClass('hidden');
            $('#button_black').removeClass('hidden');
            $('#button_reset').removeClass('hidden');
        }
    });
    
    function updateCounter(elementId, newCount, callback) {
        const $counter = $(elementId);
        $counter.fadeOut(100, function() {
            $counter.text(newCount).fadeIn(100);
            callback();
        });
    }

    function fetchCounts() {
        $.getJSON('/counts', function(data) {
            const newWhiteCount = parseInt(data.count_white);
            const newBlackCount = parseInt(data.count_black);
            
            if (newWhiteCount !== white_count) {
                white_count = newWhiteCount;
                updateCounter('#count_white', white_count, function() {
                    checkWinner();
                    updateInstructions();
                });
            }
            
            if (newBlackCount !== black_count) {
                black_count = newBlackCount;
                updateCounter('#count_black', black_count, function() {
                    checkWinner();
                    updateInstructions();
                });
            }
        });
    }
    
    setInterval(fetchCounts, 50);

    // DEBUGGING BUTTONS
    $('#button_white').click(function() {
        $.post('/button_white');
    });
    $('#button_black').click(function() {
        $.post('/button_black');
    });
    $('#button_reset').click(function() {
        $.post('/reset');
    });
});