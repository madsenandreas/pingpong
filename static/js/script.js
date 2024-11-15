let white_count = 0;
let black_count = 0;
let chosen_index = null;
let confettiInterval = null;
let current_server = null;
let starting_server = Math.random() < 0.5 ? 'Red starts serving!' : 'Blue starts serving!';
// Team name pairs from different franchises
const teamNames = [
    {white: "Fellowship", black: "Mordor", franchise: "Lord of the Rings"},
    {white: "Jedi", black: "Sith", franchise: "Star Wars"},
    {white: "Federation", black: "Klingon", franchise: "Star Trek"},
    {white: "Dumbledore's Army", black: "Death Eaters", franchise: "Harry Potter"},
    {white: "The Doctor", black: "Dalek", franchise: "Doctor Who"},
    {white: "X-Men", black: "Brotherhood", franchise: "X-Men"},
    {white: "Zion", black: "Machine", franchise: "Matrix"},
    {white: "Serenity", black: "Alliance", franchise: "Firefly"},
    {white: "Winchester", black: "Demons", franchise: "Supernatural"}
];

function updateCounter(elementId, newCount, callback) {
    const $counter = $(elementId);
    $counter.fadeOut(100, function() {
        $counter.text(newCount).fadeIn(100);
        callback();
    });
}

function updateTeamNames() {
    let new_index;
    do {
        new_index = Math.floor(Math.random() * teamNames.length);
    } while (new_index === chosen_index);
    
    chosen_index = new_index;
    const teams = teamNames[chosen_index];
    $('#white_side_name').text(teams.white);
    $('#black_side_name').text(teams.black);
}

function animatePanel(winner, loser, duration) {
    $(`.${winner}-half`).animate({width: '100%'}, duration);
    $(`.${loser}-half`).animate({width: '0%'}, duration);
}

function showCake(side) {
    $('.cake').css({
        'bottom': '-100%',
        [side]: '45%'
    }).removeClass('hidden')
      .animate({bottom: '-10%'}, 1000);
}

function throwConfetti(color, intensity) {
    const colors = color === 'white' ? 
        ['#ffffff', '#f0f0f0', '#e0e0e0'] :
        ['#000000', '#202020', '#404040'];
        
    confetti({
        particleCount: intensity === 'high' ? 150 : 100,
        spread: intensity === 'high' ? 200 : 150,
        origin: { y: 0.6 },
        colors: colors
    });
}

function startConfettiInterval(color, intensity) {
    if (confettiInterval) {
        clearInterval(confettiInterval);
    }
    confettiInterval = setInterval(() => throwConfetti(color, intensity), 500);
}

function checkWinner() {
    if (white_count === 0 && black_count === 0) {
        // Reset panels to original state
        $('.white-half, .black-half').animate({width: '50%'}, 500);
        $('.cake').addClass('hidden').css('bottom', '-100%');
        if (confettiInterval) {
            clearInterval(confettiInterval);
            confettiInterval = null;
        }
        $(".server-info").fadeIn(500);
        updateTeamNames();
        return;
    }

    if (white_count >= 11) {
        if (black_count === 0) {
            $(".server-info").fadeOut(500);
            animatePanel('white', 'black', 1000);
            showCake('right');
            startConfettiInterval('black', 'high');
        } else {
            $(".server-info").fadeOut(500);
            animatePanel('white', 'black', 1000);
            startConfettiInterval('black', 'normal');
        }
    } else if (black_count >= 11) {
        if (white_count === 0) {
            $(".server-info").fadeOut(500);
            animatePanel('black', 'white', 1000);
            showCake('left');
            startConfettiInterval('white', 'high');
        } else {
            $(".server-info").fadeOut(500);
            animatePanel('black', 'white', 1000);
            startConfettiInterval('white', 'normal');
        }
    }
}

function updateInstructions() {
    const method = (white_count > 0 || black_count > 0) ? 'fadeOut' : 'fadeIn';
    $('.instructions')[method](500);
}

const socket = io();

socket.on('game_state', function(data) {
    const newWhiteCount = parseInt(data.count_white);
    const newBlackCount = parseInt(data.count_black);
    
    const updateCallback = () => {
        checkWinner();
        updateInstructions();
    };
    
    if (newWhiteCount !== white_count) {
        white_count = newWhiteCount;
        updateCounter('#count_white', white_count, updateCallback);
    }
    
    if (newBlackCount !== black_count) {
        black_count = newBlackCount;
        updateCounter('#count_black', black_count, updateCallback);
    }

    if (current_server != data.current_server) {
        if (data.current_server === 'white') {
            current_server = 'white';
            $('.server-info')
                .animate({right: '100%'}, 200, function() {
                    $(this)
                        .removeClass('black-server-side')
                        .addClass('white-server-side')
                        .css({right: '', left: '0'})
                        .animate({left: '0'}, 200);
                });
        } else if (data.current_server === 'black') {
            current_server = 'black';
            $('.server-info')
                .animate({left: '100%'}, 200, function() {
                    $(this)
                        .removeClass('white-server-side')
                        .addClass('black-server-side')
                        .css({left: '', right: '0'})
                        .animate({right: '0'}, 200);
                });
        }
    }
    $('#serves_remaining').text(data.serves_remaining);
});

$(document).ready(function() {
    updateTeamNames();

    socket.emit('debug_request');
    socket.on('debug_response', function(data) {
        if (data.debug) {
            $('#button_white, #button_black, #button_reset, #button_white_decrement, #button_black_decrement').removeClass('hidden');
        }
    });

    $('#button_white').click(() => socket.emit('button_press', { button: 'white' }));
    $('#button_black').click(() => socket.emit('button_press', { button: 'black' }));
    $('#button_reset').click(() => socket.emit('reset_request'));
    $('#button_white_decrement').click(() => socket.emit('button_press', { button: 'white_decrement' }));
    $('#button_black_decrement').click(() => socket.emit('button_press', { button: 'black_decrement' }));
});