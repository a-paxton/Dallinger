trial = 0;
lock = true;

create_agent = function() {
    reqwest({
        url: "/node/" + participant_id,
        method: 'post',
        type: 'json',
        success: function (resp) {
            my_node_id = resp.node.id;
            get_infos();
        },
        error: function (err) {
            console.log(err);
            err_response = JSON.parse(err.response);
            if (err_response.hasOwnProperty('html')) {
                $('body').html(err_response.html);
            } else {
                allow_exit();
                go_to_page('debriefing')
            }
        }
    });
};

// Get all the infos
get_infos = function() {
    reqwest({
        url: "/node/" + my_node_id + "/infos",
        method: 'get',
        data: {info_type: "LearningGene"},
        type: 'json',
        success: function (resp) {
            learning_strategy = resp.infos[0].contents;
            get_received_infos();
        },
        error: function (err) {
            console.log(err);
            err_response = JSON.parse(err.response);
            $('body').html(err_response.html);
        }
    });
};

get_received_infos = function() {
    reqwest({
        url: "/node/" + my_node_id + "/" + received_infos,
        method: 'get',
        type: 'json',
        success: function (resp) {

            trial = trial + 1;
            $("#trial-number").html(trial);
            if (trial <= num_practice_trials) {
                $("#practice-trial").html("This is a practice trial");
            } else {
                $("#practice-trial").html("This is NOT a practice trial");
            }


            // Show the participant the stimulus.
            if (learning_strategy === "asocial") {

                $("#instructions").text("Are there more blue or yellow dots?");

                state = resp.info.contents;
                regenerateDisplay(state);

                $("#more-blue").addClass('disabled');
                $("#more-yellow").addClass('disabled');

                presentDisplay();

                $("#stimulus-stage").show();
                $("#response-form").hide();
                $("#more-yellow").show();
                $("#more-blue").show();
            }

            // Show the participant the hint.
            if (learning_strategy == "social") {

                $("#instructions").html("Are there more blue or yellow dots?");

                $("#more-blue").addClass('disabled');
                $("#more-yellow").addClass('disabled');

                meme = resp.info.contents;

                if (meme == "blue") {
                    $("#stimulus").attr("src", "/static/images/blue_social.jpg");
                } else if (meme == "yellow") {
                    $("#stimulus").attr("src", "/static/images/yellow_social.jpg");
                }
                $("#stimulus").show();
                setTimeout(function() {
                    $("#stimulus").hide();
                    $("#more-blue").removeClass('disabled');
                    $("#more-yellow").removeClass('disabled');
                    lock = false;
                }, 2000);
            }
        },
        error: function (err) {
            console.log(err);
            err_response = JSON.parse(err.response);
            $('body').html(err_response.html);
        }
    });
};

function presentDisplay (argument) {
    for (var i = dots.length - 1; i >= 0; i--) {
        dots[i].show();
    }
    setTimeout(function() {
        for (var i = dots.length - 1; i >= 0; i--) {
            dots[i].hide();
        }
        $("#more-blue").removeClass('disabled');
        $("#more-yellow").removeClass('disabled');
        lock = false;
        paper.clear();
    }, 1000);

}

function regenerateDisplay (state) {

    // Display parameters
    width = 600;
    height = 400;
    numDots = 80;
    dots = [];
    blueDots = Math.round(state * numDots);
    yellowDots = numDots - blueDots;
    sizes = [];
    rMin = 10; // The dots' minimum radius.
    rMax = 20;
    horizontalOffset = (window.innerWidth - width) / 2;

    paper = Raphael(horizontalOffset, 200, width, height);

    colors = [];
    colorsRGB = ["#428bca", "#FBB829"];

    for (var i = blueDots - 1; i >= 0; i--) {
        colors.push(0);
    }

    for (var i = yellowDots - 1; i >= 0; i--) {
        colors.push(1);
    }

    colors = shuffle(colors);

    while (dots.length < numDots) {

        // Pick a random location for a new dot.
        r = randi(rMin, rMax);
        x = randi(r, width - r);
        y = randi(r, height - r);

        // Check if there is overlap with any other dots
        pass = true;
        for (var i = dots.length - 1; i >= 0; i--) {
            distance = Math.sqrt(Math.pow(dots[i].attrs.cx - x, 2) + Math.pow(dots[i].attrs.cy - y, 2));
            if (distance < (sizes[i] + r)) {
                pass = false;
            }
        }

        if (pass) {
            var dot = paper.circle(x, y, r);
            dot.hide();
            // use the appropriate color.
            dot.attr("fill", colorsRGB[colors[dots.length]]); // FBB829
            dot.attr("stroke", "#fff");
            dots.push(dot);
            sizes.push(r);
        }
    }
}

function randi(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function shuffle(o){
    for(var j, x, i = o.length; i; j = Math.floor(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);
    return o;
}

reportBlue = function () {
    if(lock === false) {
        $("#more-blue").addClass('disabled');
        $("#more-blue").html('Sending...');
        $("#reproduction").val("");

        reqwest({
            url: "/info/" + my_node_id,
            method: 'post',
            data: {
                contents: "blue",
                info_type: "Meme"
            },
            success: function (resp) {
                $("#more-blue").removeClass('disabled');
                $("#more-blue").blur();
                $("#more-blue").html('Blue');
                createAgent();
            }
        });
        lock = true;
    }
};

reportYellow = function () {
    if(lock === false) {
        $("#more-yellow").addClass('disabled');
        $("#more-yellow").html('Sending...');
        $("#reproduction").val("");

        reqwest({
            url: "/info/" + my_node_id,
            method: 'post',
            data: {
                contents: "yellow",
                info_type: "Meme"
            },
            success: function (resp) {
                $("#more-yellow").removeClass('disabled');
                $("#more-yellow").blur();
                $("#more-yellow").html('Yellow');
                createAgent();
            }
        });
        lock = true;
    }
};

$(document).keydown(function(e) {
    var code = e.keyCode || e.which;
    if(code == 70) { //Enter keycode
        reportBlue();
    } else if (code == 74) {
        reportYellow();
    }
});

$("#more-yellow").click(function() {
    reportYellow();
});

$("#more-blue").click(function() {
    reportBlue();
});