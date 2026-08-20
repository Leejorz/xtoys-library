var multiUserMode = getVariable("multi-user-mode");
var multiusertease = multiUserMode != null;
function isMultiUserTease() {
    return multiusertease;
}
console.log("Is multiuser tease :" + multiusertease);
console.log(multiUserMode);
console.log(getVariable("username"))
var sessionUsers = {};

var useXtoysFunctions = true;
var categories = [];
var tagsPageLength = 20;
var indexLocation = "https://raw.githubusercontent.com/Leejorz/xtoys-library/main/index.json";
var indexHashLocation = "https://raw.githubusercontent.com/Leejorz/xtoys-library/main/index-hash.sha";
var currentIndexHash = null;
var activeVideoName = "";
var activeTag = "";
var patternActions = {};
var scripts = {};
var videoCount = 0;
var defaultImage = "fun";
var tags = [];
var videos = [];
var videoNamesAsInFiles = [];
var activeSearchWord = "";
var videoStarted = false;
var singleChannelDevice = "generic-1-a";
var dualChannelDevice = "generic-1|generic-1-a";
var single2ChannelDevice = "generic-1-b";
var strokerDevice = "part-linear-actuator-position-a";
var max_image_cache = 100;
var allDevices = [
    singleChannelDevice,
    dualChannelDevice,
    single2ChannelDevice,
    strokerDevice,
];
var scriptIndex = [];
var connectedBlocks = getConnectedBlocks();
var activeBlockTypes = [];
var patternPlaying;
var videoMenuOpen = false;
var rampupTime = null;
var rampupMin = null;
var rampupMax = null;
var channelDelayEnabled = false;
var channelDelay = 0.0;
var debugVariable = getVariable("debug") == "ON";
var phone = getVariable("phone") == "ON";
var pageLength = phone ? 4 : 8;
var oldstatusJson = null;
var status = null;

var sync = false;
var switchChannels = false;
var channelDelayFirst = 1;
var intensityPatternDevices = ["part-vibrator", "part-linear-actuator-a"];
var intensityPatternDeviceNames = ["hismith"];
var imageUrls = {
    loading: "https://external-preview.redd.it/5IWh1Q2ekzpLv9HrH6Q5CPsB3G6UVgCmGJNFFnDU89Y.jpg?auto=webp&s=3aeec78766a889945c84b01877c33d4fc6df3569",
    tags: "https://i.redd.it/6xgm02n1oo9a1.png",
    initializing: "https://i.redd.it/bzgg8qvim7s51.jpg",
    videos: "https://external-preview.redd.it/LzdMrhGeGeR4c2y3ZdF2x4mqWZuiSb3dIW33POofVHY.jpg?auto=webp&s=addce128b61f9479f98c77cbb3661555187a594d",
};
var videoImageCache = {};
console.log(connectedBlocks);
var estimAvailable = false;
var singleChannelAvailable = false;
var dualChannelAvailable = false;
var single2ChannelAvailable = false;
var strokerAvailable = false;
var previous_pages = [];
//showImageFromUrl(imageUrls["initializing"]);


var currentUser = isHost() ? "host" : null;
var progressBarCanvasWidth = 800;
var progressBarCanvasHeight = 400;

var progressBarWidth = 400;
var progressBarHeight = 50;
var progressBarX = (progressBarCanvasWidth - progressBarWidth) / 2;
var progressBarY = (progressBarCanvasHeight - progressBarHeight) / 2;
var innerMargin = 2;
var _progressBarFillColor;
var _progressBarBackgroundColor;
var _labelColor;
var _labelPrefix;
var _previousPercent;
var _progressBarBackgroundImage;
var _interval;
setupListeners();
if (isMultiUserTease() && isHost()) {
    callAction({ "type": "updateQueue", "action": "add", "queue": "indexcheck", "job": "indexcheck" });
}
console.log("Cookies: " + getVariable('cookies'));

function getCookies() {
    var cookies = getVariable('cookies');
    if (!cookies) {
        cookies = {};
    } else {
        cookies = JSON.parse(cookies);
    }
    return cookies;
}

function getCookie(key) {
    var cookies = getCookies();
    return cookies[key];    
}

function saveCookie(key, value) {
    var cookies = getCookies();
    cookies[key]=value;
    saveCookies(cookies);
}

function saveCookies(cookies) {
    var json = JSON.stringify(cookies);
    console.log("Saving cookies: " + json);
    setVariable("cookies", json);
}

function addToCookieArray(key, value) {
    var cookie = getCookie(key);
    if(!cookie) {
        cookie = [];
    }
    cookie.push(value);
    saveCookie(key, cookie);
}

function addToVideoHistory(videoName) {
    console.log("Adding to video history cookie: " + videoName);
    var videoHistory = getCookie("video_history");
    if(!videoHistory) {
        videoHistory = [];
    }
    if (videoHistory) {
        for (var i=0; i<videoHistory.length; i++) {
            if (videoHistory[i]['video'] == videoName) {
                videoHistory.splice(i, 1);

                break;
            }
        }
        
    }
    videoHistory.push({"video": videoName, "date": new Date()});
    saveCookie("video_history", videoHistory);
}

function getVideoNamesHistory() {
    var videoHistory = getCookie("video_history");
    var names = [];
    if(!videoHistory) {
        videoHistory = [];
    }
    if (videoHistory) {
        for (var i=0; i<videoHistory.length; i++) {
            if (videos[videoHistory[i]['video']]) {
                names.push(videoHistory[i]['video']);
            }

        }
    }
    return names;
}
function getVideoNamesFavorites() {
    var videoHistory = getCookie("favorites");
    var names = [];
    if(!videoHistory) {
        videoHistory = [];
    }
    if (videoHistory) {
        for (var i=0; i<videoHistory.length; i++) {
            if (videos[videoHistory[i]['video']]) {
                names.push(videoHistory[i]['video']);
            }
        }
    }
    return names;
}
function addToFavorites(videoName) {
    addToCookieArray("favorites", {"video": videoName, "date": new Date()});
}

function removeFromFavorites(videoName) {
    var favorites = getCookie("favorites");
    if (favorites) {
        for (var i=0; i<favorites.length; i++) {
            if (favorites[i]['video'] == videoName) {
                favorites.splice(i, 1);
                saveCookie("favorites", favorites);
                return
            }
        }
    }
}
function hasWatched(videoName) {
    var video_history = getCookie("video_history");
    if (video_history) {
        for (var i=0; i<video_history.length; i++) {
            if (video_history[i]['video'] == videoName) {
                return true;    
            }
        }
    }
    return false;
}
function isFavorite(videoName) {
    var favorites = getCookie("favorites");
    if (favorites) {
        for (var i=0; i<favorites.length; i++) {
            if (favorites[i]['video'] == videoName) {
                return true;    
            }
        }
    }
    return false;
}

function setupProgressBar(interval, fillColor, bgColor, labelPrefix, labelTextColor, imageName) {
    _labelPrefix = labelPrefix;
    _previousPercent = 0;
    _interval = interval;
    _labelColor = labelTextColor;
    _progressBarFillColor = fillColor;
    _progressBarBackgroundColor = bgColor;
    var createCanvas = { "type": "updateTease", "part": "canvas", "action": "create", "width": "" + progressBarCanvasWidth, "height": "" + progressBarCanvasHeight };
    callAction(createCanvas, true);
    if (imageName) {
        canvas.drawImage(imageName, 0, 0, progressBarCanvasWidth, progressBarCanvasHeight);
    }
    canvas.fillStyle = bgColor;
    canvas.fillRect(progressBarX, progressBarY, progressBarWidth, progressBarHeight);
    canvas.fillStyle = fillColor;
    canvas.beginPath();
    canvas.strokeStyle = fillColor;

    canvas.rect(progressBarX, progressBarY, progressBarWidth, progressBarHeight);
    canvas.stroke();
    drawLabelProgressBar(0);
    sleep(20);
}

function clearProgressBar() {
    canvas.clearRect(progressBarX - 1, progressBarY - 1, progressBarWidth + 2, progressBarHeight + 2);
}

function deleteProgressBarCanvas() {
    callAction({ "type": "updateTease", "part": "canvas", "action": "remove" });
}

function drawLabelProgressBar(percent) {
    roundedPercent = Math.round(percent, 0);
    canvas.textAlign = 'center';
    canvas.textBaseline = 'middle';
    canvas.font = '20pt Roboto';
    canvas.fillStyle = _labelColor;
    canvas.fillText(_labelPrefix + roundedPercent + " %", progressBarX + (progressBarWidth / 2), progressBarY + (progressBarHeight / 2));
}

function updateProgressBar(percent) {

    if (Math.floor(percent / _interval) > Math.floor(_previousPercent / _interval)) {
        canvas.fillStyle = _progressBarBackgroundColor;
        canvas.fillRect(progressBarX + 1, progressBarY + 1, progressBarWidth - 2, progressBarHeight - 2);

        canvas.fillStyle = _progressBarFillColor;
        canvas.fillRect(
            progressBarX + innerMargin,
            progressBarY + innerMargin,
            percent * (progressBarWidth - (innerMargin * 2)) / 100,
            progressBarHeight - (innerMargin * 2));
        drawLabelProgressBar(percent);
    }
    _previousPercent = percent;
}

function get_unicode_circle_number(number) {
    var base_number = 10102;
    var num = base_number + (number - 1);
    var c = String.fromCharCode(num);
    return c;
}
function onScriptSetupDone(type) {
    console.log("on script setup done: " + type)
    if (type == "single" && dualChannelAvailable && single2ChannelAvailable) {
        showScriptOptionsSingle2();
        showScriptOptionsDual();
    } else if (type == "single" && dualChannelAvailable) {
        showScriptOptionsDual();
    } else if (type == "single" && single2ChannelAvailable) {
        showScriptOptionsSingle2();
    } else if (type == "dual" && single2ChannelAvailable) {
        showScriptOptionsSingle2();
    } else {
        activeTag = "LATEST";
        showVideosDialog(activeTag, 0, "");
    }
}

displayTextAndWait("Initializing...", 0, "none", true);

setup();
function checkandupdateIndex() {
    var indexHash = (getXhr(indexHashLocation) || "").trim();
    if (indexHash != currentIndexHash) {
        notifyIndexChanged(indexHash);
        displayText("Index was changed, updating...", 0, "none", true);

        setup();
    }

}

function onIndexChanged(hash) {
    displayText("Host detected an index change, updating...", 0, "none", true);
    setup();

}
function setup() {
    console.log("setup");

    // The index can change while this script stays alive. Clear all state that
    // is derived from index.json before reloading it, otherwise removed videos
    // and old thumbnail data can survive an index refresh.
    videos = [];
    videoNamesAsInFiles = [];
    tags = [];
    videoImageCache = {};

    showImageFromLibrary("fun");
    setupProgressBar(5, "#f4b5f2", "white", "Loading index: ", "black", null);

    for (var i = 0; i < Object.keys(connectedBlocks).length; i++) {
        var type = Object.keys(connectedBlocks)[i];
        var devices = connectedBlocks[type];
        if (devices && devices.length > 0) {
            activeBlockTypes.push(type);
        }
    }
    console.log("Active block types: " + activeBlockTypes);
    estimAvailable = activeBlockTypes.indexOf("part-estim|part-estim-a") != -1;
    singleChannelAvailable = activeBlockTypes.indexOf("generic-1-a") != -1;
    dualChannelAvailable = activeBlockTypes.indexOf("generic-1|generic-1-a") != -1 || estimAvailable;
    single2ChannelAvailable = activeBlockTypes.indexOf("generic-1-b") != -1;
    strokerAvailable = activeBlockTypes.indexOf(strokerDevice) != -1;
    console.log("Active block types: " + activeBlockTypes);
    console.log("dualChannelAvailable: " + dualChannelAvailable);

    if (indexLocation) {
        statusText("Loading index file...");

        updateProgressBar(10);

        var indexJson = getXhr(indexLocation);
        updateProgressBar(20);

        if (indexJson) {
            try {
                index = JSON.parse(indexJson);
                currentIndexHash = index['hash'];
                if (index.videos) {
                    var newVideos = index.videos;
                    tags = index.tags;

                    for (var j = 0; j < newVideos.length; j++) {

                        var video = newVideos[j];
                        videoNamesAsInFiles.push(video.name);
                        videos[video.name] = video;
                        updateProgressBar(Math.floor(20 + (80 * (j + 1) / newVideos.length)));

                    }
                }
            } catch (error) {
                console.log(
                    "Failed to load: " + indexLocation + "\nError: " + error
                );
            }
        } else {
            console.log("Failed to load " + indexLocation);
        }


        console.log(Object.keys(videos).length + " videos available.");
        // videos.reverse();
        clearStatusText();
        deleteProgressBarCanvas();

        var patterns = [];
        if (singleChannelAvailable) {
            showScriptOptionsSingle();
        } else if (dualChannelAvailable) {
            showScriptOptionsDual();
        } else if (single2ChannelAvailable) {
            showScriptOptionsSingle2();
        } else {
            activeTag = "LATEST";

            showVideosDialog(activeTag, 0, "");
        }
    } else {
        displayText("No index fils provided...");
    }
}

function showNoDevicesWarning() {
    var buttons = [];
    buttons.push({
        name: "No",
        action: null,
        setVariable: true,
        variable: "noDeviceWarning",
        variableValue: "NO",
    });
    buttons.push({
        name: "Yes",
        action: null,
        setVariable: true,
        variable: "noDeviceWarning",
        variableValue: "YES",
    });
    statusText("No devices connected!");

    displayText("No devices connected, do you want to continue?");

    callAction({
        type: "updateTease",
        part: "input",
        inputType: "buttons",
        buttons: buttons,
    });
}

function onNoDeviceWarningChanged(yesNo) {
    console.log("no device result: " + yesNo)
    if (yesNo == "YES") {
        clearText();

        setup();
    } else {
        console.log("Calling stop tease!")
        stopTease();
    }
}

function loadScript() {
    console.log("Loading scripts for " + activeVideoName);
    var video = videos[activeVideoName];
    if (video && video.scripts) {
        console.log(
            "Loading script: " + video.scripts[scriptIndex["single"]].location
        );
        try {
            var scriptJson = getXhr(video.scripts[0].location);
        } catch (e) {
            console.log("Error calling " + video.scripts[0].location);
        }
        if (scriptJson) {
            var script = JSON.parse(scriptJson);
            scripts = {};
            scripts["single"] = script;
            scripts["dual"] = script;
            scripts["single2"] = script;
            scripts["stroker"] = script;
            debug("Scripts loaded: " + Object.keys(scripts));
            loadPatterns();
        } else {
            console.log("Script not found! " + video.scripts);
            displayText("Script not found!");
        }
    } else {
        console.log("Script not found! ");
        displayText("Script not found!");
    }
}

function playVideo(videoName) {
    console.log("Playing video " + videoName);
    activeVideoName = videoName;
    videoStarted = false;
    actions = [];
    videoMenuOpen = false;
    rampupMin = null;
    rampupMax = null;
    rampupTime = null;
    var video = videos[activeVideoName];
    scripts = {};
    patternActions = {};
    clearCanvas();
    displayText("Playing video " + videoName);
    loadScript();
    loadVideo();
}
function navigateToActivity(activity) {
    if (activity.type === "showVideosDialog") {
        showVideosDialog(activity.name, activity.page, activity.searchword);
    } else if (activity.type === "showVideoMenu") {
        onVideoChanged(activity.activeVideoName);
    } else if (activity.type === "tags") {
        showTagsDialog(activity.tags);
    } else if (activity.type == "showUserDetails") {
        showUserDetails(activity.username);
    } else if (activity.type == "showUsersDialog") {
        showUsersDialog(activity.page);
    }
}
function previous_page_called() {
    console.log("previous_page_called: " + JSON.stringify(previous_pages));
    if (previous_pages && previous_pages.length >= 2) {
        previous_page = previous_pages.slice(-2)[0];
        previous_pages = previous_pages.slice(0, -2)
        if (previous_page) {
            console.log("Previous page: " + JSON.stringify(previous_page));
            if (previous_page) {
                console.log("Not null= " + previous_page.type);
                navigateToActivity(previous_page);
            }
        }
    } else {
        console.log("No previous page!")
    }
}

function reloadPage() {
    console.log("reloadPage: " + JSON.stringify(previous_pages));
    if(previous_pages && previous_pages.length >= 1) {
        previous_page = previous_pages.slice(-1)[0];
        previous_pages = previous_pages.slice(0, -1)
        if (previous_page) {
          console.log("Previous page: "+ JSON.stringify(previous_page));
          if (previous_page) {
            console.log("Not null= " + previous_page.type);
              navigateToActivity(previous_page);
          }
        }
    } else {
      console.log("No previous page!")
    }
  }

function showTagsDialog(page) {
    console.log("showTagsDialog(" + page + ")");
    showImageFromUrl(imageUrls["tags"]);
    add_to_history({ "type": "tags", "key": page });
    clearText();
    statusText("Tags");
    var tagNames = Object.keys(tags).sort();
    var buttons = [];
    var totalPages = Math.max(1, Math.ceil(tagNames.length / tagsPageLength));
    var pageText =
        totalPages > 1 ? "[Page " + (page + 1) + "/" + totalPages + "]: " : "";
    statusText(pageText + tagNames.length + " tags available");
    var pageStart = page * tagsPageLength;
    var pageEnd = Math.min(tagsPageLength * (page + 1) - 1, tagNames.length - 1);
    var sideButtons = [];
    sideButtons.push({
        name: "All",
        action: null,
        setVariable: true,
        variable: "tagChoice",
        variableValue: "ALL",
    });
    if (previous_pages) {
        sideButtons.push({
            name: "Previous",
            action: null,
            setVariable: true,
            variable: "previous",
            variableValue: "previous",
        });
    }
    addMultiUserButtons(sideButtons);
    sideButtons.push({
        name: "☌ Search",
        action: null,
        setVariable: true,
        variable: "doSearch",
        variableValue: "true",
    });

    var randomVideoName = getRandomVideo(Object.keys(videos));
    if (randomVideoName) {
        sideButtons.push({
            name: "🎲 Random video",
            action: null,
            setVariable: true,
            variable: "videoChoice",
            variableValue: encodeURIComponent(randomVideoName),
        });
    }
    if (tagNames.length > 0) {
        if (page > 0) {
            sideButtons.push({
                name: "↑",
                action: null,
                setVariable: true,
                variable: "tagsPage",
                variableValue: page - 1,
            });
        }
        var sortTagNames = tagNames.sort();
        for (var i = pageStart; i <= pageEnd; i++) {
            buttons.push({
                name: sortTagNames[i],
                action: null,
                setVariable: true,
                variable: "tagChoice",
                variableValue: sortTagNames[i],
            });
        }
        if (page < totalPages - 1) {
            sideButtons.push({
                name: "↓",
                action: null,
                setVariable: true,
                variable: "tagsPage",
                variableValue: page + 1,
            });
        }
        displayText("Choose the tags you want to watch:");
        showSideButtons(sideButtons);
        showBottomButtons(buttons);
    } else {
        displayText("No tags found...");
    }
}

function createButtonForOthersViewings() {
    console.log("createButtonForOthersViewings: " + JSON.stringify(status));
    if (status) {
        return {
            name: "Currently watched",
            action: null,
            setVariable: true,
            variable: "navigate",
            variableValue: "currentlywatched",
        };
    }
    return null;
}


function search(videoArray, searchKeyword) {
    var searchResults = [];
    var indexes = [];

    if (searchKeyword) {
        var lowerKeyWord = searchKeyword.toLowerCase();
        for (var i = 0; i < videoArray.length; i++) {
            if (videoArray[i].toLowerCase().indexOf(lowerKeyWord) >= 0) {
                searchResults.push(videoArray[i]);
            }
        }
    }

    return searchResults;
}

function onDoSearch() {
    showSearch();
}

function onSearchChanged(keyword) {
    if (keyword != -1) {
        activeSearchWord = keyword;
        activeTag = "ALL";
        showVideosDialog(activeTag, 0, keyword);
        setVariable("search", -1);
    }
}

function getRandomVideo(videoNames) {
    if (videoNames.length > 0) {
        var random = randomNumber(0, videoNames.length - 1);
        var videoname = videoNames[random];
        return videoname;
    }
    return null;
}

function randomNumber(min, max) {
    return Math.floor(
        Math.random() * (parseInt(max) - parseInt(min) + 1) + parseInt(min)
    );
}

function showSearch() {
    statusText("Search: ");
    displayText("Search...", 0, "none", true);
    addSearch("");
}


function wrap(str) {
    return str.replace(
        /(?![^\n]{1,28}$)([^\n]{28})\s/g, '$1\n');
}

function getLatestVideos(max) {
    if (max) {
        var cutoff = Math.max(0, videoNamesAsInFiles.length - max);
        var videos_names = videoNamesAsInFiles.slice(cutoff);
    } else {
        var videos_names = videoNamesAsInFiles.slice(0);
    }
    return videos_names; // .slice().reverse();
}

function getPageItems(currentVideos, page) {
    var totalPages = Math.max(1, Math.ceil(currentVideos.length / pageLength));
    var pageStart = page * pageLength;
    var pageEnd = Math.min(pageLength * (page + 1) - 1, currentVideos.length - 1);
    var pageVideos = [];
    for (var i = pageStart; i <= pageEnd; i++) {
        pageVideos.push(currentVideos[i]);
    }
    return pageVideos;
}

function getCurrentlyWatchingUsersForVideo(videoname) {
    if (status) {
        var videonames = Object.keys(status['videos'])
        if (status['videos'][videoname] && status['videos'][videoname]['users']) {
            var users = [];
            for (var i = 0; i < status['videos'][videoname]['users'].length; i++) {
                var username = status['videos'][videoname]['users'][i];
                if (username != currentUser) {
                    users.push(username);
                }
            }
            return users;
        }
    }

    return null;
}

function getFollowing() {
    if (currentUser && status['users'][currentUser] && status['users'][currentUser]['following']) {
        return status['users'][currentUser]['following'];
    }
    return null;
}
function showUserDetails(username) {
    add_to_history({ "type": "showUserDetails", "username": username });
    clearText();
    clearCanvas();
    var buttons = [];
    var sideButtons = [];
    var othersButton = createButtonForOthersViewings();
    if (othersButton) {
        sideButtons.push(othersButton);
    }
    var following = getFollowing();
    if (following) {
        sideButtons.push({
            name: "Unfollow " + following,
            action: null,
            setVariable: true,
            variable: "follow",
            variableValue: null
        });
    }
    if (previous_pages) {
        sideButtons.push({
            name: "↰ Previous",
            action: null,
            setVariable: true,
            variable: "previous",
            variableValue: "previous",
        });
    }
    sideButtons.push({
        name: "↰ Latest",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "LATEST",
    });
    sideButtons.push({
        name: "↰ Tags",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "tags",
    });
    sideButtons.push({
        name: "↰ History",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "History",
    });
    sideButtons.push({
        name: "💜 Favorites",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "Favorites",
    });
    statusText("User details: " + username);
    console.log("Show user details for " + username + ": " + JSON.stringify(status));

    if (status && status['users'] && status['users'][username]) {
        //displayText(username, 0, "none", true);
        showSideButtons(sideButtons);
        var following = getFollowing();
        if (following == username) {
            buttons.push({
                name: "Unfollow " + following,
                action: null,
                setVariable: true,
                variable: "follow",
                variableValue: null
            });
        } else {
            buttons.push({
                name: "Follow " + username,
                action: null,
                setVariable: true,
                variable: "follow",
                variableValue: encodeURIComponent(username),
            });
        }
        showBottomButtons(buttons);

    } else {
        displayText(username + " is no longer in the session", 0, "none", true);
        showSideButtons(sideButtons);
    }
}

function onFollow(username) {

    var username = decodeURIComponent(username);
    console.log("onFollow: " + username);
    if(username == "null") {
        username == null;
    }
    notifyFollow(username);
}

function getUsersWithoutCurrentUser() {
    var usersWithoutMe = [];
    if (status && status['users']) {
        var users = Object.keys(status['users']);
        for (var i = 0; i < users.length; i++) {
            if (users[i] != currentUser) {
                usersWithoutMe.push(users[i]);
            }
        }
    }
    return usersWithoutMe;
}
function showUsersDialog(page) {
    add_to_history({ "type": "showUsersDialog", "page": page });
    clearText();
    clearCanvas();
    var buttons = [];
    var sideButtons = [];
    var othersButton = createButtonForOthersViewings();
    if (othersButton) {
        sideButtons.push(othersButton);
    }
    var following = getFollowing();
    if (following) {
        sideButtons.push({
            name: "Unfollow " + following,
            action: null,
            setVariable: true,
            variable: "follow",
            variableValue: null
        });
    }
    if (previous_pages) {
        sideButtons.push({
            name: "↰ Previous",
            action: null,
            setVariable: true,
            variable: "previous",
            variableValue: "previous",
        });
    }
    sideButtons.push({
        name: "↻ Refresh",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "users",
    });
    sideButtons.push({
        name: "↰ Latest",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "LATEST",
    });
    sideButtons.push({
        name: "↰ Tags",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "tags",
    });
    var users = getUsersWithoutCurrentUser();
    if (users) {
        var totalPages = Math.max(1, Math.ceil(users.length / pageLength));
        if (page > pageLength) {
            page = pageLength;
        }
        var pagedUsers = getPageItems(users, page)
        console.log("Pagedusers: " + pagedUsers);
        for (var i = 0; i < pagedUsers.length; i++) {
            var user = pagedUsers[i];
            buttons.push({
                name: user,
                action: null,
                setVariable: true,
                variable: "userChoice",
                variableValue: encodeURIComponent(user),
            });
        }
        var pageText =
            totalPages > 1 ? "[Page " + (page + 1) + "/" + totalPages + "]: " : "";
        statusText(
            pageText +

            users.length +
            " users available"
        );
        if (page > 0) {
            sideButtons.push({
                name: "↑",
                action: null,
                setVariable: true,
                variable: "usersPage",
                variableValue: page - 1,
            });
        }
        if (page < totalPages - 1) {
            sideButtons.push({
                name: "↓",
                action: null,
                setVariable: true,
                variable: "videosPage",
                variableValue: page + 1,
            });
        }
        showSideButtons(sideButtons);
        showBottomButtons(buttons);

    } else {
        displayText("No users found...", 0, "none", true);
        showSideButtons(sideButtons);

    }
}

function addMultiUserButtons(buttons) {
    if (isMultiUserTease()) {
        buttons.push({
            name: "↰ Users",
            action: null,
            setVariable: true,
            variable: "navigate",
            variableValue: "users",
        });
        var following = getFollowing();
        if (following) {
            buttons.push({
                name: "Unfollow " + following,
                action: null,
                setVariable: true,
                variable: "follow",
                variableValue: null
            });
        }
        var othersButton = createButtonForOthersViewings();
        if (othersButton) {
            buttons.push(othersButton);
        }
    }

}
function showVideosDialog(name, page, searchword) {
    clearText();
    console.log("showVideosDialog: " + name + " " + page + "+ " + searchword);
    //showImageFromUrl(imageUrls["videos"]);
    add_to_history({ "type": "showVideosDialog", "name": name, "page": page, "searchword": searchword });
    var currentVideos;
    if (name == "ALL") {
        currentVideos = Object.keys(videos);
    } else if (name == "LATEST") {
        currentVideos = getLatestVideos(null);
    } else if (name == "Currently watched") {
        if (status && status['videos']) {
            currentVideos = Object.keys(status['videos']);
        } else {
            currentVideos = [];
        }
    } else if (name == "History") {
        currentVideos = getVideoNamesHistory(); // .slice().reverse();
    } else if (name == "Favorites") {
        currentVideos = getVideoNamesFavorites();

    } else {
        currentVideos = tags[name]; // .slice().reverse();
    }
    if (searchword) {
        currentVideos = search(currentVideos, searchword);
    }

    var totalPages = Math.max(1, Math.ceil(currentVideos.length / pageLength));
    var pageStart = page * pageLength;
    var pageEnd = Math.min(pageLength * (page + 1) - 1, currentVideos.length - 1);
    var sideButtons = [];
    var buttons = [];

    var pageText =
        totalPages > 1 ? "[Page " + (page + 1) + "/" + totalPages + "]: " : "";
    statusText(
        pageText +
        (searchword ? "search: " + searchword : name) +
        ": " +
        currentVideos.length +
        " videos available"
    );
    console.log("Page start: " + pageStart + ", Page End: " + pageEnd + ", Total pages: " + totalPages);
    addMultiUserButtons(sideButtons);
    sideButtons.push({
        name: "↰ Tags",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "tags",
    });
    sideButtons.push({
        name: "↰ History",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "History",
    });
    sideButtons.push({
        name: "💜 Favorites",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "Favorites",
    });
    sideButtons.push({
        name: "↰ Search",
        action: null,
        setVariable: true,
        variable: "doSearch",
        variableValue: "true",
    });
    if (previous_pages) {
        sideButtons.push({
            name: "↰ Previous",
            action: null,
            setVariable: true,
            variable: "previous",
            variableValue: "previous",
        });
    }
    if (currentVideos.length > 0) {
        var randomVideoName = getRandomVideo(currentVideos);
        if (randomVideoName) {
            sideButtons.push({
                name: "🎲 Random video",
                action: null,
                setVariable: true,
                variable: "videoChoice",
                variableValue: encodeURIComponent(randomVideoName),
            });
        }
        if (page > 0) {
            sideButtons.push({
                name: "↑",
                action: null,
                setVariable: true,
                variable: "videosPage",
                variableValue: parseInt(page) - 1,
            });
        }
        var nextVideos = [];
        var currentPageVideos = getPageItems(currentVideos, page);
        console.log("currentPageVideos:" + currentPageVideos);
        for (var i = 0; i < currentPageVideos.length; i++) {
            var video = currentPageVideos[i];
            var videoName = video;
            var number = get_unicode_circle_number(i + 1);
            var favorite_text = isFavorite(videoName) ? " 💜" : "";
            buttons.push({
                
                name:  wrap(number + ' ' + videos[videoName].displayName).split("\n")[0] + favorite_text,
                action: null,
                setVariable: true,
                variable: "videoChoice",
                variableValue: encodeURIComponent(videoName),
            });
        }

        if (page < totalPages - 1) {
            sideButtons.push({
                name: "↓",
                action: null,
                setVariable: true,
                variable: "videosPage",
                variableValue: parseInt(page) + 1,
            });
            var videosToLoad = [];
            for (var t = page + 1; t < totalPages - 1 && t <= page + 1; t++) {
                var nextPageVideos = getPageItems(currentVideos, t);
                if (nextPageVideos) {
                    for (var ni = 0; ni < nextPageVideos.length; ni++) {
                        videosToLoad.push(nextPageVideos[ni]);
                    }
                    downloadThumbnails(videosToLoad);
                }
            }

        }
        drawVideosMenu(currentPageVideos);

        showBottomButtons(buttons);
        showSideButtons(sideButtons);

    } else {
        clearCanvas();
        displayText("No videos found...", 0, "none", true);
        showSideButtons(sideButtons);
    }
}
function clearCanvas() {
    //callAction({"type":"updateTease","part":"canvas","width":"0","height":"0"}, true);
    callAction({ "type": "updateTease", "part": "canvas", "action": "remove", "clear": true }, true);
}
function downloadVideoImage(videoName) {
    //console.log("Downloading thumbnail for " + videoName);
    var thumbNail = videos[videoName]["thumbnail"];
    var data = "oops"
    if (thumbNail) {
        try {
            content = getXhr(thumbNail);
            if (content) {
                data = content;
            }
        } catch (e) {
            console.log(e);
        }

    }
    return data;
}

function limitThumbnailCache() {
    var keys = Object.keys(videoImageCache);
    if (keys.length > max_image_cache) {
        var sliced_keys = keys.slice(0, keys.length - max_image_cache);
        for (var i = 0; i < sliced_keys.length; i++) {
            delete videoImageCache[sliced_keys[i]];
        }
        console.log("Reduced image cache from " + keys.length + " to " + Object.keys(videoImageCache).length);

    }
}

function getThumbnailCacheKey(videoName) {
    var video = videos[videoName];
    var thumbnail = video && video["thumbnail"] ? video["thumbnail"] : "";
    return videoName + "|" + thumbnail;
}

function downloadThumbnailAndStoreInCache(videoName) {
    var cacheKey = getThumbnailCacheKey(videoName);
    if (!videoImageCache[cacheKey]) {
        var data = downloadVideoImage(videoName);
        videoImageCache[cacheKey] = data;
        limitThumbnailCache();
    }
}

function downloadThumbnails(videoNames) {
    for (var ni = 0; ni < videoNames.length; ni++) {
        var videoName = videoNames[ni];
        var cacheKey = getThumbnailCacheKey(videoName);
        if (!videoImageCache[cacheKey]) {
            callAction({ "type": "updateQueue", "queue": "images", "action": "add", "job": "downloadImages", "variables": [{ "name": "videoname", "expression": videoName }] }, false);
        }
    }
}

function getVideoImage(videoName) {
    var cacheKey = getThumbnailCacheKey(videoName);
    if (!videoImageCache[cacheKey]) {
        var data = downloadVideoImage(videoName);
        videoImageCache[cacheKey] = data;
        limitThumbnailCache();
    }
    return videoImageCache[cacheKey];
}
function drawVideosMenu(videoNames) {
    var columns = phone ? 2 : 4;
    var rows = Math.ceil(videoNames.length / columns);
    var image_width = 256;
    var image_height = 144;
    var marging_hor = 10;
    var marging_ver = 80;
    var text_margin = 16
    var top_margin = 10;
    var left_margin = 10;
    var text_height = 100;
    var border = 5;
    var item_width = (image_width + (border + 2) + marging_hor);
    var item_height = (image_width + (border + 2) + marging_hor);

    var width = item_width * columns;
    var height = item_height * rows;
    callAction({ "type": "updateTease", "part": "canvas", "width": "" + width, "height": "" + height, "clear": true }, true);
    canvas.clearRect(0, 0, width, height);
    var index = 0;
    console.log("drawVideosMenu: " + videoNames);
    for (var y = 0; y < rows; y++) {
        for (var x = 0; x < columns; x++) {
            if (videoNames.length > index) {
                var videoName = videoNames[index];
                var isFavoriteVideo = isFavorite(videoName);
                var title = videos[videoName].displayName;
                var hasWatchedVideo = hasWatched(videoName);
                var data = getVideoImage(videoName);

                var circle_number = get_unicode_circle_number(index + 1);
                top_y = y * item_width;
                top_x = x * item_height;
  
                canvas.fillStyle = "#FFFFFF";
                canvas.fillRect(top_x, top_y, image_width + (border * 2), image_height + text_height + (border));
                canvas.fillStyle = "#000000";
                canvas.strokeRect(top_x, top_y, image_width + (border * 2), image_height + text_height + (border));


                try {
                    if (data) {
                        canvas.drawImage(data, top_x + border, top_y + border, image_width, image_height);
                    }
                } catch (e) {
                    console.log("Thumbnail draw failed for " + videoName + ": " + e);
                }
                sleep(0.1);

                canvas.beginPath();
                canvas.arc(top_x + border + 2 + 8.5, top_y + border + 2 + 9, 7, 0, 2 * Math.PI);
                canvas.fillStyle = "black";
                canvas.fill();

                canvas.textAlign = 'left';
                canvas.textBaseline = 'top';
                canvas.font = '15pt DejaVu Sans Mono';

                canvas.fillStyle = "#FFFFFF";
                canvas.fillText(circle_number, top_x + border + 2, top_y + border + 2);
                
                if(isFavoriteVideo || hasWatchedVideo) {
                    canvas.fillStyle = "#FFFFFF";
                    canvas.textAlign = 'right';
                    canvas.textBaseline = 'top';
                    var text = isFavoriteVideo ? "💜" : (hasWatchedVideo ? "⏿" :"");
                    canvas.fillText(text, top_x + image_width, top_y + border + 2);

                }
                canvas.textAlign = 'left';

                canvas.font = '10pt Roboto';
                canvas.fillStyle = "rgba(0, 0, 0, 1)";
 
                wrapped_text = wrap(title);
                lines = wrapped_text.split("\n");
                var created_at = videos[videoName].created_at ? videos[videoName].created_at.split("T")[0] : "";
 
                var users = getCurrentlyWatchingUsersForVideo(videoName);

                var users_text = users ? "Users watching: " + users.length : "";

                for (var i = 0; i < lines.length +1 && i < 4; i++) {
                    var text_x = top_x + border;
                    var text_y = top_y + image_height + (border * 2) + (i * text_margin);
                    if(i != 3 && lines[i]) {
                        //console.log("" + i + ": " + line + "x=" + text_x + ", y=" + text_y);
                        canvas.fillStyle = "black";
                        canvas.fillText(lines[i], text_x, text_y);

                    } else {
                        canvas.fillStyle = "gray";
                        canvas.fillText(created_at, text_x, text_y);

                    }

                }
                if (users_text) {
                    var text_x = top_x + border;
                    var text_y = top_y + image_height + (border * 2) + (4 * text_margin);
                    //console.log("" + i + ": " + line + "x=" + text_x + ", y=" + text_y);
                    canvas.fillStyle = "#ce1496";
                    canvas.fillText(users_text, text_x, text_y);
                }
                


            } else {
                return;
            }
            index++;
        }
    }

}

function showVideoMenu() {
    clearText();
    var video = videos[activeVideoName];
    add_to_history({ "type": "showVideoMenu", "activeVideoName": activeVideoName });
    addToVideoHistory(activeVideoName);

    var intensity = getVariable("intensity");
    var pattern = getVariableWithDefault("pattern", "single-normal");
    var single2pattern = getVariableWithDefault(
        "single2pattern",
        "single2-normal"
    );
    var patternTexts = [];
    if (singleChannelAvailable) {
        patternTexts.push(pattern);
    }
    if (dualChannelAvailable) {
        patternTexts.push(
            getVariableWithDefault("dual-pattern", "dual-normal-alternating")
        );
    }
    if (single2ChannelAvailable) {
        patternTexts.push(single2pattern);
    }
    var channelDelayText = channelDelayEnabled
        ? " Channel " +
        (channelDelayFirst == 1 ? 2 : 1) +
        " is delayed for " +
        channelDelay +
        "s"
        : "";

    var intensityText = isRampupEnabled()
        ? "Rampup from " +
        rampupMin +
        " to " +
        rampupMax +
        " in " +
        secondsToTime(rampupTime) +
        ""
        : "Intensity: " + intensity + "%";
    statusText(
        video.displayName +
        " - " +
        intensityText +
        (patternTexts.length > 0 ? " -  [" + patternTexts.join(",") + "]" : "") +
        channelDelayText
    );
    var buttons = [];
    var bottomButtons = [];
    addMultiUserButtons(buttons);
    buttons.push({
        name: "↰ Previous",
        action: null,
        setVariable: true,
        variable: "previous",
        variableValue: "previous",
    });
    buttons.push({
        name: "Latest",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "LATEST",
    });
    var isFavoriteVideo = isFavorite(activeVideoName);
    if (isFavoriteVideo) {
        buttons.push({
            name: "💔 Remove from favorites",
            action: null,
            setVariable: true,
            variable: "favorite_remove",
            variableValue: encodeURIComponent(activeVideoName),
        });
    } else {
        buttons.push({
                name: "💜 Add to favorites",
                action: null,
                setVariable: true,
                variable: "favorite_add",
                variableValue: encodeURIComponent(activeVideoName),
            });
    }
    buttons.push({
        name: "↰ History",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "History",
    });
    buttons.push({
        name: "💜 Favorites",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "Favorites",
    });
    if (true) {
        /**buttons.push({
          "name": "↦ Hide menu",
          "setVariable": true,
          "variable": "videoMenuOpen",
          "variableValue": 'OFF'
        }); */
        buttons.push({
            name: "Tags",
            action: null,
            setVariable: true,
            variable: "navigate",
            variableValue: "tags",
        });

        var following = getFollowing();
        if (following) {
            buttons.push({
                name: "Unfollow " + following,
                action: null,
                setVariable: true,
                variable: "follow",
                variableValue: null
            });
        }
        var randomVideoName = getRandomVideo(Object.keys(videos));
        if (randomVideoName) {
            buttons.push({
                name: "🎲 Random video",
                action: null,
                setVariable: true,
                variable: "videoChoice",
                variableValue: encodeURIComponent(randomVideoName),
            });
        }

        if (!videoStarted) {
            buttons.push({
                name: "Ramp-up",
                action: null,
                setVariable: true,
                variable: "rampup-menu",
                variableValue: "true",
            });
        }
        if (scripts["single"]) {
            if (video.scripts && singleChannelAvailable) {
                var blockType = getBlockType(singleChannelDevice);

                buttons.push({
                    name: "↰ Script options (" + blockType + ")",
                    action: null,
                    setVariable: true,
                    variable: "navigate",
                    variableValue: "scriptoptionssingle",
                });
            }
            if (video.scripts && dualChannelAvailable) {
                var blockType = getBlockType(dualChannelDevice);

                buttons.push({
                    name: "↰ Script options (" + blockType + ")",
                    action: null,
                    setVariable: true,
                    variable: "navigate",
                    variableValue: "scriptoptionsdual",
                });
            }
            if (video.scripts && single2ChannelAvailable) {
                var blockType = getBlockType(single2ChannelDevice)

                buttons.push({
                    name: "↰ Script options (" + blockType + ")",
                    action: null,
                    setVariable: true,
                    variable: "navigate",
                    variableValue: "scriptoptionssingle2",
                });
            }
            if (dualChannelAvailable && !videoStarted) {
                buttons.push({
                    name: "↰ Dual channel options",
                    action: null,
                    setVariable: true,
                    variable: "navigate",
                    variableValue: "dualChannel",
                });
            }

            if (!videoStarted) {
                buttons.push({
                    name: "Start manually",
                    action: null,
                    setVariable: true,
                    variable: "startmanually",
                    variableValue: "true",
                });
            } else {
                buttons.push({
                    name: "⎋ Pattern playback options",
                    action: null,
                    setVariable: true,
                    variable: "navigate",
                    variableValue: "pattternPlayBackOptions",
                });
                buttons.push({
                    name: "↻ Restart pattern",
                    action: null,
                    setVariable: true,
                    variable: "restartPattern",
                    variableValue: "true",
                });
                buttons.push({
                    name: "↻ Restart Video",
                    action: null,
                    setVariable: true,
                    variable: "restartVideo",
                    variableValue: "true",
                });
            }

            if (videoStarted && !isRampupEnabled()) {
                buttons.push({
                    name: "⇡ Intensity",
                    setVariable: true,
                    variable: "intensityControl",
                    variableValue: "+",
                });

                buttons.push({
                    name: "⇣ Intensity",
                    setVariable: true,
                    variable: "intensityControl",
                    variableValue: "-",
                });
            } else {
            }
        }
    } else {
        bottomButtons.push({
            name: "↤ Show menu",
            setVariable: true,
            variable: "videoMenuOpen",
            variableValue: "ON",
        });
    }
    var extraText = "";
    if (scripts["single"]) {
        if (videoStarted) {
            var firstActionTime = getFirstActionTime();
            var lastActionTime = getLastActionTime();

            extraText =
                "Activity time range: " +
                msToTime(firstActionTime) +
                " - " +
                msToTime(lastActionTime);
        } else {
            extraText =
                "The pattern will start when the video is started.\nOn android, use Start Manually";
        }
    } else {
        extraText = "Script not found!";
    }
    var creatorText = video.creator ? "\nScript created by " + video.creator : "";
    var texts = [];
    if (creatorText) {
        texts.push(creatorText);
    }
    try {
        var created_at = video.created_at ? "Created on: " + video.created_at.split("T")[0] : "";
        if (created_at) {
            texts.push(created_at);
        }
    } catch (error) {
        console.error(error)
    }
    var sourceText = video.url ? "Source: " + video.url : "";
    if (sourceText) {
        texts.push(sourceText);
    }
    texts.push(extraText);
    var users = getCurrentlyWatchingUsersForVideo(activeVideoName);
    if (users) {
        texts.push("Currently watching: " + users.join(", "));
    }
    displayTags(video.tags, texts.join("\n"));
    //showBottomButtons(bottomButtons);
    showBottomButtons(buttons);
}

function onVideoMenuOpenChanged() {
    videoMenuOpen = getVariable("videoMenuOpen") == "ON";
    showVideoMenu();
}

function showBottomButtons(buttons) {
    if (buttons) {
        callAction({
            type: "updateTease",
            part: "input",
            inputType: "buttons",
            buttons: buttons,
        });
    }
}

function formatScriptName(scriptName) {
    if (scriptName) {
        return scriptName.replace(".funscript", "");
    }
    return "default";
}

function showStartAtOptions(time, error) {
    clearText();
    var video = videos[activeVideoName];

    statusText("Continue pattern from a given time for " + video.displayName);
    displayText(
        "Pick the time to continue the pattern from (format '5:42' or '1:14:23'):" +
        (error ? "\nPlease provide a valid time:" : ""),
        0,
        "none",
        true
    );

    callAction({
        type: "updateTease",
        part: "input",
        location: "main",
        delay: "reading",
        text: {
            ops: [
                {
                    attributes: {
                        align: "center",
                    },
                    insert: time,
                },
            ],
        },
        inputType: "text",
        variable: "startAtTime",
        immediate: "startAtTimeIncomplete",
    });
}

function showRampupMinMenu() {
    clearText();
    var video = videos[activeVideoName];

    statusText("Ramp up minimum intensity for " + video.displayName);
    displayText("Pick the minimum intensity for the ramp-up:", 0, "none", true);

    var buttons = [];
    for (i = 0; i <= 9; i++) {
        var value = i * 10 + "";
        buttons.push({
            name: value + " %",
            action: null,
            setVariable: true,
            variable: "rampup-min-user",
            variableValue: value,
        });
    }
    showBottomButtons(buttons);
}

function showRampupMaxMenu() {
    clearText();
    var video = videos[activeVideoName];

    statusText("Ramp up maximum intensity for " + video.displayName);
    displayText("Pick the maximum intensity for the ramp-up:", 0, "none", true);

    var buttons = [];

    for (i = rampupMin / 10 + 1; i <= 10; i++) {
        var value = i * 10 + "";
        buttons.push({
            name: value + " %",
            action: null,
            setVariable: true,
            variable: "rampup-max-user",
            variableValue: value,
        });
    }
    showBottomButtons(buttons);
}

function showRampupTimeMenu(error) {
    clearText();
    statusText("Ramp up duration:");
    var firstActionTime = getFirstActionTime();
    var lastActionTime = getLastActionTime();
    var duration = lastActionTime - firstActionTime;
    var durationAsTime = msToTime(duration);
    var maxTime = "\nMax duration: " + durationAsTime;
    extraText =
        "Activity time range: " +
        msToTime(firstActionTime) +
        " - " +
        msToTime(lastActionTime);

    displayText(
        extraText +
        "\nPick the duration to ramp up from the first activity time.\n" +
        maxTime +
        " (format '5:42' or '1:14:23'):" +
        (error ? "\nPlease provide a valid time:" : ""),
        0,
        "none",
        true
    );

    var buttons = [];
    var values = [1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 45, 60];
    for (i = 0; i < values.length; i++) {
        var value = values[i];
        if (value * 60 < duration / 1000) {
            buttons.push({
                name: value + "m",
                action: null,
                setVariable: true,
                variable: "rampup-time-user",
                variableValue: secondsToTime(value * 60),
            });
        }
    }
    buttons.push({
        name: "Max time: " + durationAsTime,
        action: null,
        setVariable: true,
        variable: "rampup-time-user",
        variableValue: durationAsTime,
    });

    buttons.push({
        name: "Custom time",
        action: null,
        setVariable: true,
        variable: "rampup-custom",
        variableValue: "true",
    });
    showBottomButtons(buttons);
}

function showRampupCustomMenu(error) {
    clearText();
    statusText("Ramp up duration:");
    var firstActionTime = getFirstActionTime();
    var lastActionTime = getLastActionTime();
    var duration = lastActionTime - firstActionTime;

    var maxTime = "\nMax duration: " + msToTime(duration);
    extraText =
        "Activity time range: " +
        msToTime(firstActionTime) +
        " - " +
        msToTime(lastActionTime);

    displayText(
        extraText +
        "\nPick the duration to ramp up from the first activity time.\n" +
        maxTime +
        " (format '5:42' or '1:14:23')\nType 'back' to go back:" +
        (error ? "\nPlease provide a valid time:" : ""),
        0,
        "none",
        true
    );

    callAction({
        type: "updateTease",
        part: "input",
        location: "main",
        delay: "reading",
        text: {
            ops: [
                {
                    attributes: {
                        align: "center",
                    },
                    insert: "",
                },
            ],
        },
        inputType: "text",
        variable: "rampup-time-user",
        immediate: "rampup-time-user-incomplete",
    });
}

function onRampupTimeChanged(newRampupTime) {
    clearText();
    if (scripts["single"]) {
        if (newRampupTime.toLowerCase() == "back") {
            showRampupTimeMenu();
        } else {
            var firstActionTime = getFirstActionTime();
            var lastActionTime = getLastActionTime();
            var duration = Math.floor((lastActionTime - firstActionTime) / 1000);
            var seconds = timeToSeconds(newRampupTime);
            if (seconds >= 0 && seconds <= duration) {
                rampupTime = seconds;
                showVideoMenu();
            } else {
                showRampupTimeMenu("invalid time");
            }
        }
    }
}

function onRampupMinChanged(newRampupMin) {
    rampupMin = parseInt(newRampupMin);
    showRampupMaxMenu();
}

function onRampupMaxChanged(newRampupMax) {
    rampupMax = parseInt(newRampupMax);
    showRampupTimeMenu();
}

function showPatternPlayBackOptions() {
    clearText();
    var video = videos[activeVideoName];

    var buttons = [];
    buttons.push({
        name: "↰ Video menu",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "video",
    });

    buttons.push({
        name: "↦ Continue pattern",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "startAtOptions",
    });
    if (patternPlaying) {
        buttons.push({
            name: "◾ Stop pattern",
            action: null,
            setVariable: true,
            variable: "stopPattern",
            variableValue: "true",
        });
    }
    buttons.push({
        name: "↻ Restart pattern",
        action: null,
        setVariable: true,
        variable: "restartPattern",
        variableValue: "true",
    });
    showBottomButtons(buttons);
}

function showScriptOptionsSingle() {
    clearText();
    var video = videos[activeVideoName];
    var buttons = [];
    if (activeVideoName) {
        buttons.push({
            name: "↰ Video menu",
            action: null,
            setVariable: true,
            variable: "navigate",
            variableValue: "video",
        });
    }
    var pattern = getVariable("pattern");

    if (singleChannelAvailable) {
        var blockType = getBlockType(singleChannelDevice)
        statusText("Script options for " + blockType);
        if (pattern != "single-normal") {
            buttons.push({
                name: "Normal",
                action: null,
                setVariable: true,
                variable: "pattern",
                variableValue: "single-normal",
            });
        }
        if (pattern != "single-smooth") {
            buttons.push({
                name: "Smooth",
                action: null,
                setVariable: true,
                variable: "pattern",
                variableValue: "single-smooth",
            });
        }
        if (pattern != "intensity") {
            buttons.push({
                name: "Intensity",
                action: null,
                setVariable: true,
                variable: "pattern",
                variableValue: "single-intensity",
            });
        }
        if (pattern != "inverse") {
            buttons.push({
                name: "Inverse",
                action: null,
                setVariable: true,
                variable: "pattern",
                variableValue: "single-inverse",
            });
        }
    }
        console.log(video);
    if (video) {
        if (video.scripts) {
            var selectedScript = video.scripts[scriptIndex["single"]];
            displayText(
                "Currently selected script: " +
                formatScriptName(selectedScript.name) +
                (pattern ? " [" + pattern + "]" : ""),
                0,
                "none",
                true
            );
        }
        for (i = 0; i < video.scripts.length; i++) {
            var name = formatScriptName(video.scripts[i].name);
            buttons.push({
                name: name,
                action: null,
                setVariable: true,
                variable: "scriptIndex",
                variableValue: i + "|single",
            });
        }
    } else {
        var blockType = getBlockType(singleChannelDevice)

        displayText(
            "Script options for " + blockType + ":",
            0,
            "none",
            true
        );
    }
    callAction({
        type: "updateTease",
        part: "input",
        inputType: "buttons",
        buttons: buttons,
    });
}

function showScriptOptionsDual() {
    clearText();
    var video = videos[activeVideoName];
    var buttons = [];
    if (activeVideoName) {
        buttons.push({
            name: "↰ Video menu",
            action: null,
            setVariable: true,
            variable: "navigate",
            variableValue: "video",
        });
    }
    var dualPattern = getVariable("dual-pattern");
    if (dualChannelAvailable) {
        blockType = getBlockType(dualChannelDevice)
        statusText("Script options for " + blockType);

        if (dualPattern != "dual-smooth-alternating") {
            buttons.push({
                name: "Smooth Alternating",
                action: null,
                setVariable: true,
                variable: "dual-pattern",
                variableValue: "dual-smooth-alternating",
            });
        }
        if (dualPattern != "dual-normal-alternating") {
            buttons.push({
                name: "Normal Alternating",
                action: null,
                setVariable: true,
                variable: "dual-pattern",
                variableValue: "dual-normal-alternating",
            });
        }
        if (dualPattern != "dual-smooth-synchronous") {
            buttons.push({
                name: "Smooth Synchronous",
                action: null,
                setVariable: true,
                variable: "dual-pattern",
                variableValue: "dual-smooth-synchronous",
            });
        }
        if (dualPattern != "dual-smooth-inverse-synchronous") {
            buttons.push({
                name: "Smooth Inverse Synchronous",
                action: null,
                setVariable: true,
                variable: "dual-pattern",
                variableValue: "dual-smooth-inverse-synchronous",
            });
        }
        if (dualPattern != "dual-normal-synchronous") {
            buttons.push({
                name: "Normal Synchronous",
                action: null,
                setVariable: true,
                variable: "dual-pattern",
                variableValue: "dual-normal-synchronous",
            });
        }
    }
    if (video) {
        if (video.scripts) {
            var selectedScript = video.scripts[scriptIndex["dual"]];
            displayText(
                "Currently selected script: " +
                formatScriptName(selectedScript.name) +
                (dualPattern ? " [" + dualPattern + "]" : ""),
                0,
                "none",
                true
            );
        }
        for (i = 0; i < video.scripts.length; i++) {
            var name = formatScriptName(video.scripts[i].name);
            buttons.push({
                name: name,
                action: null,
                setVariable: true,
                variable: "scriptIndex",
                variableValue: i + "|dual",
            });
        }
    } else {
        var blockType = getBlockType(dualChannelDevice)

        displayText(
            "Select your script options for " + blockType + ":",
            0,
            "none",
            true
        );
    }
    callAction({
        type: "updateTease",
        part: "input",
        inputType: "buttons",
        buttons: buttons,
    });
}
function getBlockType(deviceType) {
    if (connectedBlocks[deviceType]) {
        var types = []
        for (i = 0; i < connectedBlocks[deviceType].length; i++) {
            types.push(connectedBlocks[deviceType][i]['blockType']);
        }
        return types.join(", ");
    }
    return null;
}

function showScriptOptionsSingle2() {
    clearText();
    var video = videos[activeVideoName];
    var buttons = [];
    if (activeVideoName) {
        buttons.push({
            name: "↰ Video menu",
            action: null,
            setVariable: true,
            variable: "navigate",
            variableValue: "video",
        });
    }
    var single2Pattern = getVariable("single2pattern");
    if (single2ChannelAvailable) {

        statusText("Script options for " + getBlockType(single2ChannelDevice));

        if (single2Pattern != "single2-normal") {
            buttons.push({
                name: "Normal",
                action: null,
                setVariable: true,
                variable: "single2pattern",
                variableValue: "single2-normal",
            });
        }
        if (single2Pattern != "single2-smooth") {
            buttons.push({
                name: "Smooth",
                action: null,
                setVariable: true,
                variable: "single2pattern",
                variableValue: "single2-smooth",
            });
        }
        if (single2Pattern != "intensity") {
            buttons.push({
                name: "Intensity",
                action: null,
                setVariable: true,
                variable: "single2pattern",
                variableValue: "single2-intensity",
            });
        }
        if (single2Pattern != "inverse") {
            buttons.push({
                name: "Inverse",
                action: null,
                setVariable: true,
                variable: "single2pattern",
                variableValue: "single2-inverse",
            });
        }
    }
    if (video) {
        if (video.scripts) {
            var selectedScript = video.scripts[scriptIndex["single2"]];
            displayText(
                "Currently selected script: " +
                formatScriptName(selectedScript.name) +
                (single2Pattern ? " [" + single2Pattern + "]" : ""),
                0,
                "none",
                true
            );
        }
        for (i = 0; i < video.scripts.length; i++) {
            var name = formatScriptName(video.scripts[i].name);
            buttons.push({
                name: name,
                action: null,
                setVariable: true,
                variable: "scriptIndex",
                variableValue: i + "|single2",
            });
        }
    } else {
        var blockType = getBlockType(single2ChannelDevice)

        displayText(
            "Select your script options for " + blockType + ":",
            0,
            "none",
            true
        );
    }
    callAction({
        type: "updateTease",
        part: "input",
        inputType: "buttons",
        buttons: buttons,
    });
}

function onScriptIndexChanged(newScriptIndex) {
    displayText("Updating script...", 0, "none", true);
    parts = (newScriptIndex + "").split("|");
    type = parts[1];
    scriptIndex[type] = parseInt(parts[0]);
    scripts[type] = null;
    for (i = 0; i < Object.keys(patternActions).length; i++) {
        var id = Object.keys(patternActions)[i];
        if (type == "dual" && id.indexOf("dual") > -1) {
            delete patternActions[id];
        } else {
            delete patternActions[id];
        }
    }
    loadScript();
    restartVideo();
    showVideoMenu();
    videoMenuOpen = false;
}

function onStartAtTimeChanged(startAtTime) {
    clearText();
    if (scripts["single"]) {
        var actions = getActions();
        var ms = timeToMs(startAtTime);
        if (ms >= 0) {
            clearPattern();
            clearRampup();
            if (singleChannelAvailable) {
                patternActions["short-single"] = facade_startAt(actions, ms);
            }
            if (dualChannelAvailable) {
                var dualActions = getDualChannelActions();
                a = facade_startAt(dualActions.a, ms);
                b = facade_startAt(dualActions.b, ms);
                patternActions["short-dual"] = {
                    a: a,
                    b: b,
                };
            }
            if (single2ChannelAvailable) {
                var single2Actions = getSingle2ChannelActions();
                patternActions["short-single2"] = facade_startAt(single2Actions, ms);
            }
            startManuallyWithoutRestartVideo();
        } else {
            showStartAtOptions(startAtTime, "invalid time");
        }
    }
}

function timeToSeconds(time) {
    if (time) {
        var timeParts = (time + "").split(":");
        var seconds = 0;
        for (var i = 0; i < timeParts.length; i++) {
            seconds += timeParts[i] * Math.pow(60, timeParts.length - i - 1);
        }

        return seconds;
    }
    return -1;
}

function timeToMs(time) {
    if (time) {
        return timeToSeconds(time) * 1000;
    }
    return -1;
}

function showDualChannelMenu() {
    clearText();
    statusText("Dual Channel options");
    text = channelDelayEnabled
        ? "Channel " +
        (channelDelayFirst == 1 ? 2 : 1) +
        " is delayed for " +
        channelDelay +
        "s"
        : "No channel delay";
    displayText("Current channel delay: " + text, 0, "none", true);

    var buttons = [];
    buttons.push({
        name: "↰ Video menu",
        action: null,
        setVariable: true,
        variable: "navigate",
        variableValue: "video",
    });
    buttons.push({
        name: "Swith channels",
        action: null,
        setVariable: true,
        variable: "dualChannelControl",
        variableValue: "all|switch-channels",
    });
    buttons.push({
        name: "Delay channel",
        action: null,
        setVariable: true,
        variable: "dualChannelControl",
        variableValue: "all|delay-channels",
    });
    callAction({
        type: "updateTease",
        part: "input",
        inputType: "buttons",
        buttons: buttons,
    });
}

function showDelayChannelMenu() {
    debug("showDelayChannelMenu()");

    clearText();
    var video = videos[activeVideoName];

    statusText("Pick the channel delay " + video.displayName);
    displayText("Pick the channel delay time:", 0, "none", true);

    var buttons = [];
    buttons.push({
        name: "Off",
        action: null,
        setVariable: true,
        variable: "dualChannelControl",
        variableValue: "all|delay-channels|off",
    });

    var values = [
        "0.025",
        "0.05",
        "0.075",
        "0.1",
        "0.125",
        "0.15",
        "0.175",
        "0.2",
        "0.25",
        "0.3",
        "0.4",
        "0.5",
        "0.6",
        "0.7",
        "0.8",
        "0.9",
        "1",
        "2",
        "3",
        "4",
        "5",
    ];
    for (i = 0; i < values.length; i++) {
        var value = values[i];
        buttons.push({
            name: value + "s",
            action: null,
            setVariable: true,
            variable: "dualChannelControl",
            variableValue: "all|delay-channels|" + value,
        });
    }
    showBottomButtons(buttons);
}

function showDelayChannelFirstMenu() {
    debug("showDelayChannelFirstMenu()");
    clearText();
    var video = videos[activeVideoName];

    statusText("Delay channel");
    displayText("Which channel do you to delay:", 0, "none", true);

    var buttons = [];
    buttons.push({
        name: "None",
        action: null,
        setVariable: true,
        variable: "dualChannelControl",
        variableValue: "all|delay-channels-first|none",
    });
    buttons.push({
        name: "1",
        action: null,
        setVariable: true,
        variable: "dualChannelControl",
        variableValue: "all|delay-channels-first|2",
    });
    buttons.push({
        name: "2",
        action: null,
        setVariable: true,
        variable: "dualChannelControl",
        variableValue: "all|delay-channels-first|1",
    });

    showBottomButtons(buttons);
}

function callActions(actions) {
    for (var i = 0; i < actions.length; i++) {
        callAction(actions[i]);
    }
}

function onRestartPattern() {
    patternActions["short-single"] = null;
    patternActions["short-dual"] = null;
    patternActions["short-single2"] = null;
    updatePattern(
        getActions(),
        getDualChannelActions(),
        getSingle2ChannelActions(),
        getStrokerActions(),

        sync
    );

    showVideoMenu();
}

function onDualChannelControlChanged(variable) {
    var split = variable.split("|");
    var channel = split[0];
    var action = split[1];
    debug(split);
    var value = split.length > 2 ? split[2] : null;
    debug("onDualChannelControlChanged action:" + action);
    debug("onDualChannelControlChanged value:" + value);

    if ("switch-channels" == action) {
        var switchChannels =
            getVariableWithDefault("switch-channels", "OFF") == "ON";
        setVariable("switch-channels", switchChannels ? "OFF" : "ON");
        showVideoMenu();
    } else if ("delay-channels" == action) {
        if (value) {
            if (value == "off") {
                channelDelayEnabled = false;
                channelDelay = 0.0;
                patternActions = {};
                clearText();
                loadPatterns();
                restartVideo();
                showDualChannelMenu();
            } else {
                channelDelayEnabled = true;
                channelDelay = value;
                patternActions = {};
                clearText();
                loadPatterns();
                restartVideo();

                showDualChannelMenu();
            }
        } else {
            showDelayChannelFirstMenu();
        }
    } else if ("delay-channels-first" == action) {
        if (value) {
            if (value == "none") {
                channelDelayEnabled = false;
                channelDelay = 0.0;
                patternActions = {};
                clearText();
                loadPatterns();
                restartVideo();

                showDualChannelMenu();
            } else {
                channelDelayFirst = value;
                showDelayChannelMenu();
            }
        } else {
            showDelayChannelFirstMenu();
        }
    }
}

function onIntensityControlChanged(value) {
    var increment = 5;
    var intensity = getVariable("intensity");
    if (value == "+") {
        intensity = Math.min(100, intensity + increment);
    } else if (value == "-") {
        intensity = Math.max(0, intensity - increment);
    }
    setVariable("intensity", intensity);
    updateIntensity();
    showVideoMenu();
}

function onRestartVideo() {
    restartVideo();
}

function getFirstActionTime() {
    var actions = getActions();
    if (!actions) {
        actions = getDualChannelActions();
    }
    if (!actions) {
        actions = getSingle2ChannelActions();
    }
    if (!actions) {
        actions = script["single"].actions;
    }
    if (actions) {
        for (var i = 0; i < actions.length; i++) {
            if (actions[i].pos > 0) {
                return actions[i].at;
            }
        }
    }
    return null;
}

function getLastActionTime() {
    var actions = getActions();

    if (!actions) {
        actions = getDualChannelActions();
    }
    if (!actions) {
        actions = getSingle2ChannelActions();
    }
    if (!actions) {
        actions = script["single"].actions;
    }
    if (actions) {
        for (var i = actions.length - 1; i >= 0; i--) {
            if (actions[i].pos > 0) {
                return actions[i].at;
            }
        }
    }
    return null;
}

function showSideButtons(buttons) {
    callAction({
        type: "updateTease",
        part: "input",
        inputType: "side-buttons",
        buttons: buttons,
    });
}

function onPatternChanged(newPattern) {
    if (activeVideoName) {
        clearText();
        clearPattern();
        clearRampup();

        loadPatterns();
        restartVideo();
        showVideoMenu();
    } else {
        onScriptSetupDone("single");
    }
}

function onDualPatternChanged(pattern) {
    if (activeVideoName) {
        clearText();
        clearPattern();
        clearRampup();

        loadPatterns();
        restartVideo();
        showVideoMenu();
    } else {
        onScriptSetupDone("dual");
    }
}

function onSingle2PatternChanged(newPattern) {
    if (activeVideoName) {
        clearText();
        clearPattern();
        clearRampup();

        loadPatterns();
        restartVideo();
        showVideoMenu();
    } else {
        onScriptSetupDone("single2");
    }
}

function loadPatterns() {
    var pattern = getVariable("pattern");
    var dualpattern = getVariable("dual-pattern");
    var single2pattern = getVariable("single2pattern");
    debug("Load patterns: " + JSON.stringify(scripts));
    try {
        if (scripts && Object.keys(scripts).length > 0) {
            if (singleChannelAvailable) {
                debug("Load patterns singleChannelAvailable");

                script = scripts["single"];
                if (pattern == "single-smooth" && !patternActions["single-smooth"]) {
                    statusText("Smoothing pattern...");
                    loading();
                    patternActions["single-smooth"] = smoothPatternExternal(
                        script.actions
                    );
                    clearStatusText();
                }
                if (pattern == "single-inverse" && !patternActions["single-inverse"]) {
                    statusText("Inversing pattern...");
                    loading();

                    patternActions["single-inverse"] = inversePattern(script.actions);
                    clearStatusText();
                }
                if (
                    pattern == "single-intensity" &&
                    !patternActions["single-intensity"]
                ) {
                    statusText("Intensifying pattern...");
                    loading();

                    patternActions["single-intensity"] = intensityPattern(script.actions);
                    clearStatusText();
                }
            }
            if (dualChannelAvailable) {
                debug("Load patterns dualChannelAvailable");

                script = scripts["dual"];
                debug(
                    "Loading dual script, checking if notnull " +
                    (script ? "true" : "false")
                );
                debug("loadPatterns: Dual Channel available");
                if (
                    dualpattern == "dual-normal-alternating" &&
                    !patternActions["dual-normal-alternating"]
                ) {
                    statusText("Generating " + dualpattern + " pattern...");
                    loading();
                    patternActions["dual-normal-alternating"] = normalAlternatingPattern(
                        script.actions
                    );
                    clearStatusText();
                } else if (
                    dualpattern == "dual-smooth-alternating" &&
                    !patternActions["dual-smooth-alternating"]
                ) {
                    statusText("Generating " + dualpattern + " pattern...");
                    loading();
                    patternActions["dual-smooth-alternating"] = smoothAlternatingPattern(
                        script.actions
                    );
                    clearStatusText();
                } else if (
                    dualpattern == "dual-normal-synchronous" &&
                    !patternActions["dual-normal-synchronous"]
                ) {
                    statusText("Generating " + dualpattern + " pattern...");
                    loading();
                    patternActions["dual-normal-synchronous"] = normalSynchronousPattern(
                        script.actions
                    );
                    clearStatusText();
                } else if (
                    dualpattern == "dual-smooth-synchronous" &&
                    !patternActions["dual-smooth-synchronous"]
                ) {
                    statusText("Generating " + dualpattern + " pattern...");
                    loading();
                    patternActions["dual-smooth-synchronous"] = smoothSynchronousPattern(
                        script.actions
                    );
                    clearStatusText();
                } else if (
                    dualpattern == "dual-smooth-inverse-synchronous" &&
                    !patternActions["dual-smooth-inverse-synchronous"]
                ) {
                    statusText("Generating " + dualpattern + " pattern...");
                    loading();
                    patternActions["dual-smooth-inverse-synchronous"] =
                        smoothInverseSynchronousPattern(script.actions);
                    clearStatusText();
                } else {
                    debug("Did not do anything for dual pattern: " + dualpattern);
                }
            }
            if (single2ChannelAvailable) {
                debug("Load patterns single2ChannelAvailable");

                script = scripts["single2"];
                if (
                    single2pattern == "single2-smooth" &&
                    !patternActions["single2-smooth"]
                ) {
                    statusText("Smoothing pattern...");
                    loading();
                    patternActions["single2-smooth"] = smoothPatternExternal(
                        script.actions
                    );
                    clearStatusText();
                }
                if (
                    single2pattern == "single2-inverse" &&
                    !patternActions["single2-inverse"]
                ) {
                    statusText("Inversing pattern...");
                    loading();

                    patternActions["single2-inverse"] = inversePattern(script.actions);
                    clearStatusText();
                }
                if (
                    single2pattern == "single2-intensity" &&
                    !patternActions["single2-intensity"]
                ) {
                    statusText("Intensifying pattern...");
                    loading();

                    patternActions["single2-intensity"] = intensityPattern(
                        script.actions
                    );
                    clearStatusText();
                }

            }
            if (strokerAvailable) {
                script = scripts["stroker"];
                patternActions["stroker"] = script.actions;
            }
        }
    } catch (e) {
        displayText(
            "Whoops, something went wrong generating the patterns.",
            0,
            "none",
            true
        );

        throw e;
    }
}

function msToTime(s) {
    // Pad to 2 or 3 digits, default is 2
    function pad(n, z) {
        console.log("pad" + n + " " + z)
        z = z || 2;
        return ("00" + n).slice(-z);
    }

    var ms = s % 1000;
    s = (s - ms) / 1000;
    var secs = s % 60;
    s = (s - secs) / 60;
    var mins = s % 60;
    var hrs = (s - mins) / 60;

    return (hrs > 0 ? pad(hrs) + ":" : "") + pad(mins) + ":" + pad(secs);
}

function secondsToTime(s) {
    return msToTime(s * 1000);
}

function onVideoStarted() {
    if (scripts["single"]) {
        console.log("video started");
        updatePattern(
            getActions(),
            getDualChannelActions(),
            getSingle2ChannelActions(),
            getStrokerActions(),
            sync
        );
        videoStarted = true;
        showVideoMenu();
    }
}

function getActions() {
    if (patternActions["short-single"]) {
        return patternActions["short-single"];
    }
    if (scripts["single"]) {
        var pattern = getVariable("pattern");
        var foundActions = patternActions[pattern];
        if (foundActions) {
            return foundActions;
        }
        return scripts["single"].actions;
    }
    return null;
}

function getStrokerActions() {
    return patternActions["stroker"];
}

function getDualChannelActions() {
    if (patternActions["short-dual"]) {
        return patternActions["short-dual"];
    }
    if (scripts["dual"]) {
        var pattern = getVariable("dual-pattern");
        debug("dual channel actions:" + pattern);
        var foundActions = patternActions[pattern];
        if (foundActions) {
            return foundActions;
        }
        return scripts["dual"].actions;
    }
    return null;
}

function getSingle2ChannelActions() {
    if (patternActions["short-single2"]) {
        return patternActions["short-single2"];
    }
    if (scripts["single2"]) {
        var pattern = getVariable("single2pattern");
        debug("single2 channel actions:" + pattern);
        var foundActions = patternActions[pattern];
        if (foundActions) {
            return foundActions;
        }
        return scripts["single2"].actions;
    }
    return null;
}

function onTagChanged(tag) {
    activeTag = tag;
    showVideosDialog(tag, 0, "");
}

function onTagsPageChanged(page) {
    showTagsDialog(parseInt(page));
}

function onVideoPageChanged(page) {
    console.log('Video page: ' + page)
    showVideosDialog(activeTag, parseInt(page), activeSearchWord);
}

function onUsersPageChanged(page) {
    console.log('Users page: ' + page)
    showUsersDialog(parseInt(page));
}

function onCurrentlyWatched(page) {
    console.log('Currently watched: ' + page)
    showVideosDialog(activeTag, parseInt(page), activeSearchWord);
}

function onUserChoice(userName) {
    userName = decodeURIComponent(userName);
    showUserDetails(userName);
}

function onVideoChanged(videoName) {
    console.log("onVideoChanged(" + videoName + ")");
    videoName = decodeURIComponent(videoName);
    clearVideo();
    clearPattern();
    clearRampup();

    clearText();
    scriptIndex["single"] = 0;
    scriptIndex["dual"] = 0;
    scriptIndex["single2"] = 0;
    statusText("Loading " + videoName);

    playVideo(videoName);

    showVideoMenu();
}
function clearAll() {
    scriptIndex["single"] = 0;
    scriptIndex["dual"] = 0;
    scriptIndex["single2"] = 0;
    clearVideo();
    clearPattern();
    clearRampup();
    activeTag = "";
    
    patternActions["short-single"] = null;
    patternActions["short-dual"] = null;
    patternActions["short-single2"] = null;
    activeSearchWord = "";

}
function onNavigateChanged(text) {
    if (text) {
        setVariable("navigate", "");
        if (text === "tags") {
            clearAll();
            showTagsDialog(0);
        } else if (text === "LATEST") {
            clearAll();
            activeTag = "LATEST";
            showVideosDialog(activeTag, 0, "");
        } else if (text === "History") {
            clearAll();
            activeTag = "History";
            showVideosDialog(activeTag, 0, "");
        } else if (text === "Favorites") {
            clearAll();
            activeTag = "Favorites";
            showVideosDialog(activeTag, 0, "");
        } else if (text === "video") {
            showVideoMenu();
        } else if (text === "estim") {
            showEstimMenu();
        } else if (text == "dualChannel") {
            showDualChannelMenu();
        } else if (text == "scriptoptionssingle") {
            showScriptOptionsSingle();
        } else if (text == "scriptoptionsdual") {
            showScriptOptionsDual();
        } else if (text == "scriptoptionssingle2") {
            showScriptOptionsSingle2();
        } else if (text == "startAtOptions") {
            showStartAtOptions("00:00");
        } else if (text == "pattternPlayBackOptions") {
            showPatternPlayBackOptions();
        } else if (text == "currentlywatched") {
            clearAll();
            activeTag = "Currently watched";
            showVideosDialog(activeTag, 0, "");
        } else if (text == "users") {
            clearAll();
            showUsersDialog(0);
        }
    }
}

function onStopPatternChanged() {
    clearPattern();
    clearRampup();

    videoMenuOpen = false;
    showVideoMenu();
}

function onStartManually() {
    startManuallyWithoutRestartVideo();
    restartVideo();
}

function startManuallyWithoutRestartVideo() {
    videoMenuOpen = false;
    statusText("Press play on the video when the timer reaches 0");
    displayText(
        "The pattern will start when the timer reaches 0.\nMake sure you start the video at the same time.",
        0,
        "none",
        true
    );
    callAction({
        type: "updateTease",
        part: "timer",
        timerType: "normal",
        seconds: "3",
        setVariable: true,
        variable: "startPattern",
        stopOnStepChange: null,
        blockActions: null,
        variableValue: "true",
    });
}

function stopTease() {
    console.log("Stopping tease!");
    callAction({
        type: "updateTease",
        part: "general",
        action: "stop",
    });
}

function onManuallyStarted() {
    if (scripts["single"]) {
        updatePattern(
            getActions(),
            getDualChannelActions(),
            getSingle2ChannelActions(),
            getStrokerActions(),
            sync
        );
        videoStarted = true;
        showVideoMenu(activeVideoName);
    }
}

function updateIntensity() {
    var intensity = getVariable("intensity");

    for (var i = 0; i < activeBlockTypes.length; i++) {
        if (activeBlockTypes[i].indexOf(strokerDevice) != -1) {
            speed_action = {
                type: "updateComponent",
                channel: activeBlockTypes[i],
                action: "setVolume",
                mode: "speed",
                rampTime: 0,
                percentVolume: intensity + "",
            }
            //callAction(speed_action);
        } else {
            callAction({
                type: "updateComponent",
                channel: activeBlockTypes[i],
                action: "setVolume",
                rampTime: 0,
                percentVolume: intensity + "",
            });
        }

    }
}

function isRampupEnabled() {
    return rampupMax != null && rampupTime != null && rampupMin != null;
}

function updatePattern(actions, dualChannelActions, single2Actions, strokerActions, sync) {
    debug(
        "Update pattern, actions available: single: " + JSON.stringify(actions)
    );
    debug(
        "Update pattern, actions available: dual: " +
        JSON.stringify(dualChannelActions)
    );
    debug(
        "Update pattern, actions available: single2: " +
        JSON.stringify(single2Actions)
    );
    debug(
        "Update pattern, actions available: stroker: " +
        JSON.stringify(strokerActions)
    );
    var switchChannels = getVariableWithDefault("switch-channels", "OFF") == "ON";
    actions_to_push = [];
    if (actions || dualChannelActions || single2Actions) {
        patternPlaying = true;
        if (isRampupEnabled()) {
            startRampup();
        } else {
            updateIntensity();
        }
        if (activeBlockTypes.indexOf(singleChannelDevice) > -1) {
            actions_to_push.push({
                type: "updateComponent",
                channel: singleChannelDevice,
                action: "setPattern",
                patternAction: "specific",
                videoSync: sync,
                restart: true,
                pattern: {
                    name: "video-player",
                    type: "draw",
                    patternData: {
                        loop: true,
                        channels: 1,
                        channelData: {
                            1: actions,
                        },
                    },
                },
                patternControls: {
                    id: "off",
                },
            });
        }
        if (activeBlockTypes.indexOf(strokerDevice) > -1) {
            actions_to_push.push({
                type: "updateComponent",
                channel: strokerDevice,
                mode: "position",
                action: "setPattern",
                patternAction: "specific",
                videoSync: sync,
                restart: true,
                pattern: {
                    name: "video-player",
                    type: "draw",
                    patternData: {
                        loop: true,
                        channels: 1,
                        channelData: {
                            1: strokerActions,
                        },
                    },
                },
                patternControls: {
                    id: "off",
                },
            });
        }
        if (activeBlockTypes.indexOf(dualChannelDevice) > -1) {
            var channelActions = getChannelActions(dualChannelActions, 1);
            var secondChannelActions = getChannelActions(dualChannelActions, 2);
            actions_to_push.push({
                type: "updateComponent",
                channel: dualChannelDevice,
                action: "setPattern",
                patternAction: "specific",
                actionChannel: "all",
                videoSync: sync,
                restart: true,
                pattern: {
                    name: "video-player",
                    type: "draw",
                    patternData: {
                        loop: true,
                        channels: 2,
                        channelData: {
                            1: channelActions,
                            2: secondChannelActions,
                        },
                    },
                },
            });
        }
        if (activeBlockTypes.indexOf(single2ChannelDevice) > -1) {
            //var single2Actions = getSingle2ChannelActions();
            actions_to_push.push({
                type: "updateComponent",
                channel: single2ChannelDevice,
                action: "setPattern",
                patternAction: "specific",
                videoSync: sync,
                restart: true,
                pattern: {
                    name: "video-player",
                    type: "draw",
                    patternData: {
                        loop: true,
                        channels: 1,
                        channelData: {
                            1: single2Actions,
                        },
                    },
                },
            });
        }
        callActions(actions_to_push);
    } else {
        displayText("Script not found!");
    }
}

function getChannelActions(dualChannelActions, channel) {
    if (switchChannels) {
        if (channel == 1) {
            return dualChannelActions.b;
        } else {
            return dualChannelActions.a;
        }
    } else if (channel == 1) {
        return dualChannelActions.a;
    } else {
        return dualChannelActions.b;
    }
}

function updateSecondChannel() {
    var channel = channelDelayFirst == 1 ? 2 : 1;
    //debug('Actions for channel ' + channel + ':\n' + JSON.stringify(channelActions));
    console.log(
        new Date().getMilliseconds() + "- updating channel " + channelDelayFirst
    );
    callAction({
        type: "updateComponent",
        channel: dualChannelDevice,
        action: "setPattern",
        patternAction: "specific",
        actionChannel: channel + "",
        videoSync: sync,
        restart: true,
        pattern: {
            name: "video-player",
            type: "draw",
            patternData: {
                loop: true,
                channels: 1,
                channelData: {
                    1: secondChannelActions,
                },
            },
        },
    });
}

function displayText(text) {
    displayText(text, "none", 0, true);
}

function displayText(text, delay, delayTime, clear) {
    callAction({
        type: "updateTease",
        part: "text",
        location: "main",
        delay: delay,
        delayTime: delayTime,
        text: {
            ops: [
                {
                    attributes: {
                        bold: true,
                    },
                    insert: text,
                },
                {
                    attributes: {
                        align: "center",
                    },
                    insert: "\n",
                },
            ],
        },
        clear: clear,
    }, false);
}


function displayTextAndWait(text) {
    displayTextAndWait(text, "none", 0, true);
}

function displayTextAndWait(text, delay, delayTime, clear) {
    callAction({
        type: "updateTease",
        part: "text",
        location: "main",
        delay: delay,
        delayTime: delayTime,
        text: {
            ops: [
                {
                    attributes: {
                        bold: true,
                    },
                    insert: text,
                },
                {
                    attributes: {
                        align: "center",
                    },
                    insert: "\n",
                },
            ],
        },
        clear: clear,
    }, true);
}
function clearText() {
    callAction({
        type: "updateTease",
        part: "text",
        location: "main",
        delay: "none",
        text: {
            ops: [
                {
                    attributes: {
                        align: "center",
                    },
                    insert: "\n",
                },
            ],
        },
        clear: true,
    });
    clearSideButtons();
}

function displayTags(tags, creatorText) {
    if (tags) {
        var ops = [];
        for (var i = 0; i < tags.length; i++) {
            ops.push({
                attributes: {
                    background: "#bbbbbb",
                    bold: true,
                },
                insert: "[" + tags[i] + "]",
            });
            ops.push({
                insert: " ",
            });
        }
        ops.push({
            insert: creatorText,
        });
        callAction({
            type: "updateTease",
            part: "text",
            location: "main",
            delay: "none",
            text: {
                ops: ops,
            },
            clear: true,
        });
    }
}

function statusText(text) {
    callAction({
        type: "updateTease",
        part: "text",
        source: "media",
        location: "status",
        statusText: text,
    });
}

function restartVideo() {
    patternActions["short-single"] = null;
    patternActions["short-dual"] = null;
    patternActions["short-single2"] = null;
    videoStarted = false;
    videoMenuOpen = false;

    clearVideo();
    clearPattern();
    clearRampup();

    //Sleep is required here
    sleep(100);
    loadVideo();
    showVideoMenu();
}

function isExternalVideoSite(site) {
    var value = (site || "").toLowerCase();
    return value == "pixeldrain" || value == "pixeldrain.com" ||
        value == "hmvmania" || value == "hmvmania.com" ||
        value == "pmvhaven" || value == "pmvhaven.com" ||
        value == "rule34video" || value == "rule34video.com";
}

function loadVideo() {
    var video = videos[activeVideoName];
    console.log("Loading video: " + JSON.stringify(video));

    if (video && isExternalVideoSite(video.site)) {
        console.log("External/manual video source detected: " + video.site + " / " + video.id);
        var source = video.sourceUrl || video.url || "";
        var message = "This host cannot be embedded by the xToys tease video action. Open the source separately, start it at 0:00, then press Start manually.";
        if (source) {
            message += " Source: " + source;
        }
        statusText(message);
        return;
    }

    callAction({
        part: "video",
        site: video.site,
        type: "updateTease",
        video: video.id,
        source: "url",
    }, true);
}

function clearStatusText() {
    callAction({
        type: "updateTease",
        part: "text",
        source: "media",
        location: "status",
        statusText: "",
        clear: true,
    });
}

function clearVideo() {
    videoMenuOpened = false;
    showImage(defaultImage);
}

function showImage(image) {
    callAction({
        type: "updateTease",
        part: "image",
        source: "media",
        image: image,
    });
}
function add_to_history(obj) {
    if (previous_pages.length == 0 || JSON.stringify(previous_pages.slice(-1)[0]) != JSON.stringify(obj)) {
        notifyActivity(obj);
        previous_pages.push(obj);
        console.log("Adding history: " + JSON.stringify(obj));

    }
}
function contains(a, obj) {
    var i = a.length;
    while (i--) {
        if (a[i] === obj) {
            return true;
        }
    }
    return false;
}

function clearPattern() {
    patternPlaying = false;
    if (activeBlockTypes) {
        actions_to_do = [];
        for (var i = 0; i < activeBlockTypes.length; i++) {
            var deviceType = activeBlockTypes[i];
            console.log("Clearing " + deviceType);
            if (activeBlockTypes.indexOf(strokerDevice) > -1) {
                actions_to_do.push({ "type": "updateComponent", "channel": deviceType, "mode": "position", "action": "setPosition", "percentVolume": "0" });
            }
            actions_to_do.push({
                type: "updateComponent",
                channel: deviceType,
                action: "setPattern",
                actionChannel: "all",
                patternAction: "specific",
                pattern: {
                    custom: "Off",
                    name: "Off",
                    description: "Intensity will be at 0 even if slider is active",
                    channels: 1,
                    supportedDevices: ["generic-1"],
                    patternData: {
                        custom: "off",
                    },
                },
            });

        }
        callActions(actions_to_do);
    }
}

function clearSideButtons() {
    callAction({
        type: "updateTease",
        part: "input",
        inputType: "side-buttons",
        buttons: [
            {
                name: null,
                action: null,
            },
        ],
    });
}

function addSearch(text) {
    callAction({
        type: "updateTease",
        part: "input",
        location: "main",
        delay: "reading",
        text: {
            ops: [
                {
                    attributes: {
                        align: "center",
                    },
                    insert: text,
                },
            ],
        },
        inputType: "text",
        variable: "search",
        immediate: "searchIncomplete",
    });
}

function setTimeout2(expression, delay) {
    callAction({
        type: "updateQueue",
        queue: "timeout",
        action: "add",
        job: "timeout",
        variables: [
            {
                name: "expression",
                expression: expression,
            },
            {
                name: "delay",
                expression: delay,
            },
        ],
    });
}

function handleTimeout(expression) {
    if (expression == "delay2ndChannel") {
        updateSecondChannel();
    }
}

function startRampup() {
    var firstActionTime = getFirstActionTime();
    var startTime = Math.max(1, firstActionTime / 1000);

    console.log("Starting rampup queue");
    callAction({
        type: "updateQueue",
        code: "",
        customVar: "result",
        storeResult: false,
        queue: "rampup",
        action: "add",
        job: "Ramp-up",
        variables: [
            {
                name: "time",
                expression: rampupTime + "",
            },
            {
                name: "start-time",
                expression: startTime + "",
            },
            {
                name: "min",
                expression: rampupMin + "",
            },
            {
                name: "max",
                expression: rampupMax + "",
            },
        ],
    });
}

function clearRampup() {
    callAction({
        type: "updateQueue",
        queue: "rampup",
        action: "clear",
    });
}

function getVariableWithDefault(variableName, defaultValue) {
    var value = getVariable(variableName);
    if (value) {
        return value;
    }
    return defaultValue;
}

function loading() {
    showImageFromUrl(imageUrls["loading"]);
}

function showImageFromUrl(url) {
    clearCanvas();
    callAction({
        url: url,
        part: "image",
        site: "other",
        type: "updateTease",
        source: "url",
    }, true);
}

function showImageFromLibrary(name) {
    clearCanvas();
    callAction({ "type": "updateTease", "part": "image", "source": "media", "image": name }, true);
}

function debug(text) {
    if (isDebug()) {
        console.log(text);
    }
}

function isDebug() {
    return debugVariable;
}

function inversePattern(actions) {
    var newActions = facade_inversePattern(actions);
    var patternGenerationRate = getVariable("pattern-generation-rate");
    var patternGenerationTickMaxChange = getVariable(
        "pattern-generation-tick-max-change"
    );
    var smoothed = facade_smoothPattern(
        newActions,
        patternGenerationRate,
        patternGenerationTickMaxChange
    );
    var targetMin = getVariable("scale-min");
    var targetMax = getVariable("scale-max");

    return facade_normalizePattern(
        smoothed.actions,
        smoothed.min,
        smoothed.max,
        targetMin,
        targetMax
    );
}

function smoothPatternExternal(actions) {
    var patternGenerationRate = getVariable("pattern-generation-rate");
    var patternGenerationTickMaxChange = getVariable(
        "pattern-generation-tick-max-change"
    );
    var smoothed = facade_smoothPattern(
        actions,
        patternGenerationRate,
        patternGenerationTickMaxChange
    );
    var targetMin = getVariable("scale-min");
    var targetMax = getVariable("scale-max");

    return facade_normalizePattern(
        smoothed.actions,
        smoothed.min,
        smoothed.max,
        targetMin,
        targetMax
    );
}

function delayChannels(dualActions) {
    if (channelDelayEnabled) {
        statusText("Delaying channel ...");
        var channelDelayMs = channelDelay * 1000;
        var actionsA = dualActions.a;
        var actionsB = dualActions.b;
        if (!switchChannels) {
            if (channelDelayFirst == 1) {
                actionsB = facade_delayActions(dualActions.b, channelDelayMs);
            } else {
                actionsA = facade_delayActions(dualActions.a, channelDelayMs);
            }
        } else {
            if (channelDelayFirst == 1) {
                actionsA = facade_delayActions(dualActions.a, channelDelayMs);
            } else {
                actionsB = facade_delayActions(dualActions.b, channelDelayMs);
            }
        }
        return {
            a: actionsA,
            b: actionsB,
        };
    } else {
        return dualActions;
    }
}

function smoothAlternatingPattern(actions) {
    var patternGenerationRate = getVariable("pattern-generation-rate");
    var patternGenerationTickMaxChange = getVariable(
        "pattern-generation-tick-max-change"
    );
    var alternatiingActions = facade_alternatePattern(
        actions,
        patternGenerationRate
    );

    var smoothedA = facade_smoothPattern(
        alternatiingActions.a,
        patternGenerationRate,
        patternGenerationTickMaxChange
    );
    var smoothedB = facade_smoothPattern(
        alternatiingActions.b,
        patternGenerationRate,
        patternGenerationTickMaxChange
    );

    var targetMin = getVariable("scale-min");
    var targetMax = getVariable("scale-max");

    var normalizedActionsA = facade_normalizePattern(
        smoothedA.actions,
        smoothedA.min,
        smoothedA.max,
        targetMin,
        targetMax
    );
    var normalizedActionsB = facade_normalizePattern(
        smoothedB.actions,
        smoothedB.min,
        smoothedB.max,
        targetMin,
        targetMax
    );

    return delayChannels({
        a: normalizedActionsA,
        b: normalizedActionsB,
    });
}

function normalAlternatingPattern(actions) {
    var patternGenerationRate = getVariable("pattern-generation-rate");
    return facade_alternatePattern(actions, patternGenerationRate);
}

function smoothInverseSynchronousPattern(actions) {
    var newActions = facade_inversePattern(actions);

    var patternGenerationRate = getVariable("pattern-generation-rate");
    var patternGenerationTickMaxChange = getVariable(
        "pattern-generation-tick-max-change"
    );

    var smoothed = facade_smoothPattern(
        newActions,
        patternGenerationRate,
        patternGenerationTickMaxChange
    );
    var targetMin = getVariable("scale-min");
    var targetMax = getVariable("scale-max");

    var newActions = facade_normalizePattern(
        smoothed.actions,
        smoothed.min,
        smoothed.max,
        targetMin,
        targetMax
    );
    return delayChannels({
        a: newActions,
        b: newActions,
    });
}

function smoothSynchronousPattern(actions) {
    var patternGenerationRate = getVariable("pattern-generation-rate");
    var patternGenerationTickMaxChange = getVariable(
        "pattern-generation-tick-max-change"
    );

    var smoothed = facade_smoothPattern(
        actions,
        patternGenerationRate,
        patternGenerationTickMaxChange
    );
    var targetMin = getVariable("scale-min");
    var targetMax = getVariable("scale-max");

    var newActions = facade_normalizePattern(
        smoothed.actions,
        smoothed.min,
        smoothed.max,
        targetMin,
        targetMax
    );
    return delayChannels({
        a: newActions,
        b: newActions,
    });
}

function normalSynchronousPattern(actions) {
    return delayChannels({
        a: actions,
        b: actions,
    });
}

function intensityPosition(a0, a1) {
    return Math.min(
        100,
        Math.floor(Math.abs((a1.pos - a0.pos) / (a1.at - a0.at)) * 100)
    );
}

function createNewPositions(actions, positionFunction) {
    for (i = 0; i < actions.length - 1; i++) {
        actions[i].pos = positionFunction(actions[i], actions[i + 1]);
    }
    return actions;
}



function intensityPattern(actions) {
    var newActions = createNewPositions(actions, intensityPosition);
    var patternGenerationRate = getVariable("pattern-generation-rate");
    var patternGenerationTickMaxChange = getVariable(
        "pattern-generation-tick-max-change"
    );
    var smoothed = facade_smoothPattern(
        newActions,
        patternGenerationRate,
        patternGenerationTickMaxChange
    );
    var targetMin = getVariable("scale-min");
    var targetMax = getVariable("scale-max");
    return facade_normalizePattern(
        smoothed.actions,
        smoothed.min,
        smoothed.max,
        targetMin,
        targetMax
    );
}

function facade_alternatePattern(actions, patternGenerationRate) {
    if (useXtoysFunctions) {
        return funscript_alternatePattern(actions, patternGenerationRate);
    } else {
        return tease_alternatePattern(actions, patternGenerationRate);
    }
}

function facade_smoothPattern(
    newActions,
    patternGenerationRate,
    patternGenerationTickMaxChange
) {
    if (useXtoysFunctions) {
        return funscript_smoothPattern(
            newActions,
            patternGenerationRate,
            patternGenerationTickMaxChange
        );
    } else {
        return tease_smoothPattern(
            newActions,
            patternGenerationRate,
            patternGenerationTickMaxChange
        );
    }
}

function facade_normalizePattern(actions, min, max, targetMin, targetMax) {
    if (useXtoysFunctions) {
        return funscript_normalizePattern(actions, min, max, targetMin, targetMax);
    } else {
        return tease_normalizePattern(actions, min, max, targetMin, targetMax);
    }
}

function facade_inversePattern(actions) {
    if (useXtoysFunctions) {
        return funscript_inversePattern(actions);
    } else {
        return tease_inversePattern(actions);
    }
}

function facade_startAt(actions, startAtTimeMs) {
    //if (useXtoysFunctions) {
    //    return funscript_startAt(actions, startAtTimeMs);
    //} else {
    return tease_startAt(actions, startAtTimeMs);
    //}
}

function facade_delayActions(actions, delay) {
    if (useXtoysFunctions) {
        return funscript_delayActions(actions, delay);
    } else {
        return tease_delayActions(actions, delay);
    }
}

function tease_startAt(actions, startAtTimeMs) {
    if (actions) {
        var newActions = [];
        for (i = 0; i < actions.length; i++) {
            var action = actions[i];
            if (action.at >= startAtTimeMs) {
                if (newActions.length == 0) {
                    newActions.push({
                        at: 0,
                        pos: 0,
                    });
                }
                newActions.push({
                    at: action.at - startAtTimeMs,
                    pos: action.pos,
                });
            }
        }
        return newActions;
    }
    return actions;
}

function tease_inversePattern(actions) {
    var newpositions = [];
    for (i = 0; i < actions.length - 1; i++) {
        newpositions.push({
            at: actions[i].at,
            pos: Math.max(0, 100 - actions[i].pos),
        });
    }
    return newpositions;
}

function tease_alternatePattern(actions, patternGenerationRate) {
    var length = actions.slice(-1).pop().at;
    var normalSamples = length / patternGenerationRate;
    var fadeTime = 3000;
    var fadeSamples = fadeTime / patternGenerationRate;

    var totalSamples = normalSamples + fadeSamples * 2;
    var sample = 0;
    var actionIndex = 0;

    var a1 = actions[0];
    var a0 = a1;
    var left = [];
    var right = [];
    sample = a0.at / patternGenerationRate;
    while (sample < totalSamples) {
        var ms = sample * patternGenerationRate;

        if (a1.at < ms && actionIndex < actions.length - 1) {
            a0 = a1;
            actionIndex++;
            a1 = actions[actionIndex];
        }

        var dist = a1.at - a0.at;
        var distFromNow = a1.at - ms;

        var dpos = a1.pos - a0.pos;
        var alpha = Math.max(0, Math.min(1, (ms - a0.at) / dist)) || 0;
        var pos = Math.floor(a0.pos + dpos * alpha);
        var fade = 1;
        if (dist > fadeTime * 2) {
            if (distFromNow < fadeTime) {
                fade = Math.max(0, 1 - distFromNow / fadeTime);
            } else if (dist - distFromNow > fadeTime) {
                fade = Math.max(0, 1 - (dist - distFromNow - fadeTime) / fadeTime);
            }
        }
        left.push({
            pos: Math.floor((100 - pos) * fade),
            at: ms,
        });
        right.push({
            pos: Math.floor(pos * fade),
            at: ms,
        });

        if (fade == 0) {
            if (distFromNow - fadeTime > 0) {
                var newSample = (a1.at - fadeTime) / patternGenerationRate;
                if (newSample <= sample) {
                    sample++;
                } else {
                    sample = newSample;
                }
            } else {
                sample++;
            }
        } else {
            sample++;
        }
    }
    return {
        a: left,
        b: right,
    };
}

function tease_normalizePattern(actions, min, max, targetMin, targetMax) {
    if (actions) {
        targetMin = targetMin > 0 ? parseInt(targetMin) : 0;
        targetMax = targetMax > 0 && targetMax < 100 ? parseInt(targetMax) : 100;

        for (i = 0; i < actions.length; i++) {
            var pos = parseInt(actions[i].pos);
            var percent = (parseInt(pos) - parseInt(min)) / parseInt(max);
            var newPos = Math.floor((targetMax - targetMin) * percent + targetMin);
            actions[i].pos = newPos;
        }
    }
    return actions;
}

function tease_smoothPattern(
    actions,
    patternGenerationRate,
    patternGenerationTickMaxChange
) {
    var length = actions.slice(-1).pop().at;
    var target = 0;
    var normalSamples = length / patternGenerationRate;
    var totalSamples = normalSamples;
    var current = 0;
    var actionIndex = 0;
    var previousPosition = 0;
    var position = 0;
    var newActions = [];

    max = 0;
    min = null;
    var a1 = actions[0];
    var a0 = a1;
    var sample =
        a0.at / patternGenerationRate - 100 / patternGenerationTickMaxChange;

    while (sample < totalSamples) {
        var ms = sample * patternGenerationRate;
        if (a1.at < ms && actionIndex < actions.length - 1) {
            var old = a1;
            var positions = 0;
            previousPosition = position;
            while (a1.at < ms && actionIndex < actions.length - 1) {
                a0 = a1;
                actionIndex++;
                a1 = actions[actionIndex];
                positions += a1.pos * (a1.at - a0.at);
            }
            position = Math.floor(positions / (a1.at - old.at));
        }
        var distFromNow = a1.at - ms;
        var dpos = position - previousPosition;
        var steps = Math.ceil(Math.abs(dpos) / patternGenerationTickMaxChange);
        var samplesLeft = Math.floor(distFromNow / patternGenerationRate);

        if (steps >= samplesLeft) {
            target = position;
            if (current != target) {
                if (current < target) {
                    current += Math.min(target - current, patternGenerationTickMaxChange);
                } else {
                    current -= Math.min(current - target, patternGenerationTickMaxChange);
                }
                current = Math.min(100, Math.max(0, current));
                if (max < current) {
                    max = current;
                }
                if (min == null || min > current) {
                    min = current;
                }
                newActions.push({
                    at: ms,
                    pos: current,
                });
            }
            sample++;
        } else {
            var increase = samplesLeft - steps + 1 > 1 ? samplesLeft - steps + 1 : 1;
            sample += Math.floor(increase);
        }
    }
    return {
        min: min,
        max: max,
        actions: newActions,
    };
}

function tease_delayActions(actions, delay) {
    newActions = [];
    if (actions) {
        for (i = 0; i < actions.length; i++) {
            newActions.push({
                at: actions[i].at + delay,
                pos: actions[i].pos,
            });
        }
    }
    return newActions;
}


function isHost() {
    return multiUserMode == "host";
}

function onGuestJoined(triggerUser) {
    if (isHost()) {
        console.log(triggerUser + " joined!");
        sendIdentification(triggerUser);
        notifyStatus();
    }

}

function sendIdentification(name) {
    console.log("Sending identification for " + name);
    callAction({ "type": "multiUser", "action": "send", "multiUserAction": "identification", "users": [name], "additionalData": [{ "key": "identification", "value": name }] });
}
function onGuestLeft(triggerUser) {
    if (isHost()) {
        console.log(triggerUser + " left!");
        delete sessionUsers[triggerUser];
        var users = Object.keys(status['users']);
        for (var i = 0; i < users.length; i++) {
            var userName = users[i];
            var user = users[userName];
            if (user['following'] && user['following'] == triggerUser) {
                delete user['following'];
            }
        }
        notifyStatus();

    }

}

function setActivity(user, activity) {
    console.log("setActivity: " + JSON.stringify({ "user": user, "activity": activity }));
    if (!sessionUsers[user]) {
        sessionUsers[user] = {};
    }
    sessionUsers[user]["activity"] = activity;
}

function notifyStatus() {
    if (isHost()) {
        var status = createStatus();
        var json = JSON.stringify(status);
        var encodedjson = encodeURI(json);
        console.log("Notify status" + json);
        callAction({ "type": "multiUser", "action": "send", "multiUserAction": "status", "additionalData": [{ "key": "status", "value": encodedjson }] });
        onStatusUpdated(encodedjson);
    }
}
function onStatusUpdated(statusJson) {
    if (oldstatusJson != statusJson) {
        var decodedjson = decodeURI(statusJson);
        console.log("Watched videos json: " + decodedjson);
        status = JSON.parse(decodedjson);
        oldstatusJson = decodedjson;
    }

}
function createStatus() {
    console.log("createStatus: " + JSON.stringify(sessionUsers));
    users = Object.keys(sessionUsers);
    var localwatchedVideos = {};
    for (var i = 0; i < users.length; i++) {
        var user = users[i];
        if (sessionUsers[user]['activity']) {
            if ("showVideoMenu" == sessionUsers[user]['activity']['type']) {
                var videoName = sessionUsers[user]['activity']["activeVideoName"];
                watchedVideo = localwatchedVideos[videoName];
                if (watchedVideo) {
                    watchedVideo['users'].push(user);
                } else {
                    watchedVideo = { "users": [user] }
                }
                localwatchedVideos[videoName] = watchedVideo;
            }
        }
    }

    var videoNames = Object.keys(localwatchedVideos);
    videoNames.sort(function (a, b) {
        return (a.users ? a.users.length : 0) - (b.users ? b.users.length : 0);
    });
    var sortedVideos = {};
    var totalUsers = 0;
    for (var j = 0; j < videoNames.length; j++) {
        var videoName = videoNames[j];
        var users = localwatchedVideos[videoName]['users'];
        totalUsers += users.length;
        sortedVideos[videoName] = { 'users': users };
    }
    var payload = { "videocount": videoNames.length, "users": sessionUsers, "userswatching": totalUsers, "videos": sortedVideos };

    return payload;
}

function onUserActivity(triggerUser, activityJson) {
    var activity = JSON.parse(decodeURI(activityJson));
    setActivity(triggerUser, activity);
    notifyStatus();
    var users = Object.keys(sessionUsers);
    for (var i = 0; i < users.length; i++) {
        var username = users[i];
        var user = sessionUsers[username];
        if (user['following'] && user['following'] == triggerUser && activity) {
            forceActivity(username, activity);
        }
    }
}

function notifyActivity(obj) {
    var activity = encodeURI(JSON.stringify(obj));
    if (isHost()) {
        onUserActivity("host", activity);
    } else {
        callAction({ "type": "multiUser", "action": "send", "multiUserAction": "activity", "additionalData": [{ "key": "activity", "value": activity }] });
    }
}

function notifyIndexChanged(hash) {
    callAction({ "type": "multiUser", "action": "send", "multiUserAction": "activity", "additionalData": [{ "key": "indexChanged", "value": hash }] });

}
function onHostFollow(user, username) {
    var decodedUsername = decodeURI(username);
    if (decodedUsername == "null") {
        decodedUsername = null;
    }
    console.log("onHostFollow: " + user + " ; " + username);
    if (!sessionUsers[user]) {
        sessionUsers[user] = {};
    }
    sessionUsers[user]["following"] = decodedUsername;
    notifyStatus();
    if (decodedUsername && sessionUsers[decodedUsername] && sessionUsers[decodedUsername]['activity']) {
        forceActivity(user, sessionUsers[decodedUsername]['activity']);
    }
}

function forceActivity(username, activity) {
    var activityJson = JSON.stringify(activity);
    var encodedActivity = encodeURI(activityJson);
    console.log("Forcing activity on " + username + " : " + activityJson);
    if (username == "host") {
        onForcedActivity(username, encodedActivity);
    } else {
        callAction({ "type": "multiUser", "action": "send", "multiUserAction": "forceActivity", "users": [username], "additionalData": [{ "key": "forceActivity", "value": encodedActivity }] });
    }
}

function onForcedActivity(from, activityJson) {
    var decodedActivity = decodeURI(activityJson);
    console.log("Forced activity: " + decodedActivity);
    var activity = JSON.parse(decodedActivity);
    navigateToActivity(activity);
}

function notifyFollow(username) {
    var encodedUsername = encodeURI(username);
    if (isHost()) {
        onHostFollow("host", username);
    } else {
        callAction({ "type": "multiUser", "action": "send", "multiUserAction": "follow", "additionalData": [{ "key": "follow", "value": encodedUsername }] });
    }
    console.log("notifyFollow: " + username);
    if(username == null || username == "null") {
        reloadPage();
    }
}

function onIdentification(name) {
    console.log("onIdentification: " + name);
    currentUser = name;
}

function setupListeners() {
    registerTrigger({ "type": "teaseState", "part": "video", "event": "started" }, onVideoStarted_trigger);
    registerTrigger({ "type": "variableChange", "variable": "videoChoice","valueChange": true }, onVideoChoiceChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "navigate", "valueChange": true}, onNavigateChangedTrigger);
    registerTrigger({ "part": "video", "type": "teaseState", "event": "stopped" }, onVideoEndedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "startPattern", "valueChange": true }, onStartPatternTrigger);
    registerTrigger({ "type": "variableChange", "variable": "videosPage", "valueChange": true }, onVideoPageChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "pattern" }, onPatternChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "dual-pattern" }, onDualPatternChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "single2pattern" }, onSingle2PatternChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "restartVideo", "valueChange": true }, onRestartVideo);
    registerTrigger({ "type": "variableChange", "variable": "tagChoice", "valueChange": true }, onTagChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "search", "valueChange": null }, onSearchChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "doSearch", "valueChange": true }, onDoSearchTrigger);
    registerTrigger({ "type": "variableChange", "variable": "startmanually", "valueChange": true }, onStartManuallyTrigger);
    registerTrigger({ "type": "variableChange", "variable": "tagsPage", "valueChange": true }, onTagsPageChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "estimControl", "valueChange": true }, onEstimControlChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "intensityControl", "valueChange": true }, onIntensityControlChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "dualChannelControl", "valueChange": true }, onDualChannelControlChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "restartPattern", "valueChange": true }, onRestartPatternTrigger);
    registerTrigger({ "type": "variableChange", "variable": "noDeviceWarning", "valueChange": true }, onNoDeviceWarningChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "startAtTime", "valueChange": true }, onStartAtTimeChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "videoMenuOpen", "valueChange": true }, onVideoMenuOpenChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "rampup-min-user", "valueChange": true }, onRampupMinChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "rampup-max-user", "valueChange": true }, onRampupMaxChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "rampup-time-user", "valueChange": true }, onRampupTimeChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "rampup-menu", "valueChange": true }, showRampupMinMenuTrigger);
    registerTrigger({ "type": "variableChange", "variable": "rampup-custom", "valueChange": true }, showRampupCustomMenuTrigger);
    registerTrigger({ "type": "variableChange", "variable": "previous", "valueChange": true }, previous_page_calledTrigger);
    registerTrigger({ "type": "variableChange", "variable": "favorite_add", "valueChange": true }, favorite_add_calledTrigger);
    registerTrigger({ "type": "variableChange", "variable": "favorite_remove", "valueChange": true }, favorite_remove_calledTrigger);

    if (isMultiUserTease()) {
        setupMultiUserListeners();
    }
}


function setupMultiUserListeners() {
    console.log("Setting up multi user listeners");
    registerTrigger({ "type": "multiUser", "event": "join", "multiUserMode": "host" }, onGuestJoinedTrigger);
    registerTrigger({ "type": "multiUser", "event": "leave", "multiUserMode": "host" }, onGuestLeftTrigger);
    registerTrigger({ "type": "multiUser", "event": "action", "multiUserMode": "host", "multiUserAction": "activity" }, onUserActivityTrigger);
    registerTrigger({ "type": "multiUser", "event": "action", "multiUserMode": "both", "multiUserAction": "status" }, onStatusUpdatedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "usersPage", "valueChange": true }, onUsersPageChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "userChoice", "valueChange": true }, onUserChoiceTrigger);

    registerTrigger({ "type": "variableChange", "variable": "indexChanged" }, onIndexChangedTrigger);
    registerTrigger({ "type": "variableChange", "variable": "follow" }, onFollowTrigger);
    registerTrigger({ "type": "multiUser", "event": "action", "multiUserMode": "host", "multiUserAction": "follow" }, onHostFollowTrigger);
    registerTrigger({ "type": "multiUser", "event": "action", "multiUserMode": "guest", "multiUserAction": "forceActivity" }, onForcedActivityTrigger);
    registerTrigger({ "type": "multiUser", "event": "action", "multiUserMode": "guest", "multiUserAction": "identification" }, onIdentificationTrigger);
}




function onVideoStarted_trigger(data) {
    onVideoStarted();
}

function onVideoChoiceChangedTrigger(data) {
    console.log("onVideoChoiceChangedTrigger: " + JSON.stringify(data));
    onVideoChanged(data['trigger']);
}
function onNavigateChangedTrigger(data) {
    console.log("onNavigateChangedTrigger: " + JSON.stringify(data));
    onNavigateChanged(data['trigger']);
}
function onVideoEndedTrigger(data) {
    console.log('Video Ended')
}

function onStartPatternTrigger(data) {
    onManuallyStarted();
}
function onVideoPageChangedTrigger(data) {
    onVideoPageChanged(data['trigger']);
}
function onPatternChangedTrigger(data) {
    onPatternChanged(data['trigger']);
}
function onDualPatternChangedTrigger(data) {
    onDualPatternChanged(data['trigger']);
}
function onSingle2PatternChangedTrigger(data) {
    onSingle2PatternChanged(data['trigger']);
}
function onRestartVideoTrigger(data) {
    onRestartVideo();
}
function onTagChangedTrigger(data) {
    onTagChanged(data['trigger']);
}
function onSearchChangedTrigger(data) {
    onSearchChanged(data['trigger']);
}
function onDoSearchTrigger(data) {
    onDoSearch();
}
function onStartManuallyTrigger(data) {
    onStartManually();
}
function onTagsPageChangedTrigger(data) {
    onTagsPageChanged(data['trigger']);
}
function onTagsPageChangedTrigger(data) {
    onTagsPageChanged(data['trigger']);
}
function onEstimControlChangedTrigger(data) {
    onEstimControlChanged(data['trigger']);
}

function onIntensityControlChangedTrigger(data) {
    onIntensityControlChanged(data['trigger']);
}
function onDualChannelControlChangedTrigger(data) {
    onDualChannelControlChanged(data['trigger']);
}
function onStopPatternChangedTrigger(data) {
    onStopPatternChanged();
}
function onScriptIndexChangedTrigger(data) {
    onScriptIndexChanged(data['trigger']);
}
function onRestartPatternTrigger(data) {
    onRestartPattern();
}
function onNoDeviceWarningChangedTrigger(data) {
    onNoDeviceWarningChanged(data['trigger']);
}
function onStartAtTimeChangedTrigger(data) {
    onStartAtTimeChanged(data['trigger']);
}

function onVideoMenuOpenChangedTrigger(data) {
    onVideoMenuOpenChanged();
}
function onRampupMinChangedTrigger(data) {
    onRampupMinChanged(data['trigger']);
}
function onRampupMaxChangedTrigger(data) {
    onRampupMaxChanged(data['trigger']);
}

function onRampupTimeChangedTrigger(data) {
    onRampupTimeChanged(data['trigger']);
}
function showRampupMinMenuTrigger(data) {
    showRampupMinMenu();
}
function onRampupMaxChangedTrigger(data) {
    onRampupMaxChanged(data['trigger']);
}
function showRampupCustomMenuTrigger(data) {
    onRampupMaxChanged(data['trigger']);
}



function previous_page_calledTrigger(data) {
    previous_page_called();
}

function favorite_add_calledTrigger(data) {
    addToFavorites(decodeURIComponent(data['trigger']));
    sleep(0.5);
    showVideoMenu();
}
function favorite_remove_calledTrigger(data) {
    removeFromFavorites(decodeURIComponent(data['trigger']));
    showVideoMenu();
}
function onGuestJoinedTrigger(data) {
    onGuestJoined(data['trigger-user']);
    reloadPage();
}
function onGuestLeftTrigger(data) {
    onGuestLeft(data['trigger-user']);
}
function onUserActivityTrigger(data) {
    console.log("onUserActivityTrigger: " + JSON.stringify(data));
    onUserActivity(data['trigger-user'], data['trigger']['activity'], data['trigger']["video"]);
}
function onStatusUpdatedTrigger(data) {
    console.log("onStatusUpdatedTrigger: " + JSON.stringify(data));
    onStatusUpdated(data['trigger']['status']);
}
function onUserChoiceTrigger(data) {
    console.log("onUserChoiceTrigger: " + JSON.stringify(data));
    onUserChoice(data['trigger']);
}

function onIndexChangedTrigger(data) {
    console.log("onIndexChanged: " + JSON.stringify(data));
    onIndexChanged(data['trigger']);
}

function onFollowTrigger(data) {
    console.log("onFollowTrigger: " + JSON.stringify(data));
    onFollow(data['trigger']);
}

function onHostFollowTrigger(data) {
    console.log("onHostFollowTrigger: " + JSON.stringify(data));
    onHostFollow(data['trigger-user'], data['trigger']['follow']);
}

function onForcedActivityTrigger(data) {
    console.log("onForcedActivityTrigger: " + JSON.stringify(data));
    onForcedActivity(data['trigger-user'], data['trigger']['forceActivity']);
}

function onIdentificationTrigger(data) {
    console.log("onIdentificationTrigger: " + JSON.stringify(data));
    onIdentification(data['trigger']['identification']);
}

function onUsersPageChangedTrigger(data) {
    console.log("onUsersPageTrigger: " + JSON.stringify(data));
    onUsersPageChanged(data['trigger']);
}