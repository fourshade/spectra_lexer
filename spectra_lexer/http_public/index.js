function SpectraClient() {

    const TR_DELIM = '->';          // Delimiter between keys and letters of translations shown in title bar.
    const MORE_TEXT = '(more...)';  // Text displayed as the final match, allowing the user to expand the search.

    const NODE_SELECTOR = '.stenoGraph a';             // CSS selector for graph nodes.
    const OPT_SELECTOR = 'input[name="w_boardopts"]';  // CSS selector for board option radio elements.

    function JSONQueryParams(queryString) {
        // Construct an object from a URL query string with values in JSON format.
        let params = new URLSearchParams(queryString);
        for (let [k, v] of params) {
            try {
                this[k] = JSON.parse(v);
            } catch(e) {
                console.error(e);
            }
        }
    }
    const queryOptions = new JSONQueryParams(window.location.search);

    function elementById(id) {
        return document.getElementById(id);
    }
    const searchInput = elementById("w_input");
    const searchMatches = elementById("w_matches");
    const searchMappings = elementById("w_mappings");
    const searchModeStrokes = elementById("w_strokes");
    const searchModeRegex = elementById("w_regex");
    const displayTitle = elementById("w_title");
    const displayText = elementById("w_graph");
    const displayDesc = elementById("w_caption");
    const displayBoard = elementById("w_board");
    const displayLink = elementById("w_link");

    class ListHandler {
        constructor(root, onSelectFn) {
            this.root = root;
            this.onSelectFn = onSelectFn;
            this.active = {};
            root.addEventListener("click", this.clickEvent.bind(this));
        }
        selectElem(elem) {
            if(this.root === elem || this.active === elem) {
                return false;
            }
            this.active.className = "";
            this.active = elem;
            elem.className = 'selected';
            return true;
        }
        selectText(value) {
            for (let elem of this.root.children) {
                if(elem.textContent == value) {
                    return this.selectElem(elem);
                }
            }
        }
        clickEvent({target}) {
            if(this.selectElem(target)) {
                this.onSelectFn(target.textContent);
            }
        }
        update(optArray) {
            let lastValue = this.value;
            let root = this.root;
            while (root.firstChild) {
                root.removeChild(root.firstChild);
            }
            let fragment = document.createDocumentFragment();
            for (let opt of optArray) {
                let item = document.createElement("li");
                item.textContent = opt;
                fragment.appendChild(item);
            }
            root.appendChild(fragment);
            this.active = {};
            this.selectText(lastValue);
        }
        get value() {return this.active.textContent;}
    }
    const matchSelector = new ListHandler(searchMatches, onSelectMatch);
    const mappingSelector = new ListHandler(searchMappings, onSelectMapping);

    var lastMatches = {};
    var lastPageCount = 1;
    function doSearch() {
        let input = searchInput.value;
        sendRequest({action: "search",
                     args: [input, lastPageCount]});
    }
    function newSearch() {
        lastPageCount = 1;
        doSearch();
    }
    function onSelectMatch(match) {
        if(match == MORE_TEXT) {
            lastPageCount++;
            doSearch();
        } else {
            let mappings = lastMatches[match];
            mappingSelector.update(mappings);
            if(mappings.length) {
                querySelection(match, mappings);
            }
        }
    }
    function onSelectMapping(mapping) {
        if(mapping) {
            let match = matchSelector.value;
            querySelection(match, [mapping]);
        }
    }
    function querySelection(match, mappings) {
        // The order of lexer parameters depends on the strokes mode.
        // Currently, strokes can never have more than one mapping.
        let strokes = searchModeStrokes.checked;
        sendRequest({action: "query",
                     args: strokes ? [match, mappings[0]]: [mappings, match]});
    }
    searchModeStrokes.addEventListener("change", newSearch);
    searchModeRegex.addEventListener("change", newSearch);
    searchInput.addEventListener("input", newSearch);

    function doQuery() {
        let translation = displayTitle.value.split(TR_DELIM).map(s => s.trim()).filter(s => s);
        if(translation.length == 2) {
            sendRequest({action: "query",
                         args: translation});
        }
    }
    displayTitle.addEventListener("input", doQuery);
    $(OPT_SELECTOR).click(doQuery);

    var graphFocused = false;
    var currentLink = "";
    function setPage({graph, intense_graph, caption, board, rule_id}) {
        displayText.innerHTML = graphFocused ? intense_graph : graph;
        displayDesc.textContent = caption;
        displayBoard.innerHTML = board;
        displayLink.style.display = (rule_id ? "block" : "none");
        currentLink = rule_id;
    }
    displayLink.addEventListener("click", function(){
        sendRequest({action: "search_examples",
                     args: [currentLink],
                     ignoreCache: true});
        return false;
    });

    var currentPages = null;
    var currentDefaultPage = null;
    var currentNodeRef = null;
    function graphAction(nodeRef) {
        if(currentPages) {
            currentNodeRef = nodeRef;
            setPage(currentPages[nodeRef] || currentDefaultPage);
        }
    }
    $(displayText).on("mouseenter", NODE_SELECTOR, function(){
        if(!graphFocused) {
            let nodeRef = this.href.split("#").pop();
            if(nodeRef != currentNodeRef) {
                graphAction(nodeRef);
            }
        }
        return false;
    }).on("click", NODE_SELECTOR, function(){
        let nodeRef = this.href.split("#").pop();
        graphFocused = true;
        graphAction(nodeRef);
        return false;
    }).click(function(){
        let nodeRef = "";
        graphFocused = false;
        graphAction(nodeRef);
        return false;
    });

    function updateSearch({matches, is_complete}) {
        lastMatches = matches;
        let keys = Object.keys(matches);
        // If there are unseen results, add a final list item to allow search expansion.
        if(!is_complete) {
            keys.push(MORE_TEXT);
        }
        matchSelector.update(keys);
        // If the new list does not have the previous selection, reset the mappings.
        if(!matchSelector.value) {
            mappingSelector.update([]);
        }
        if (keys.length == 1) {
            // Automatically select the item if there was only one.
            let [match] = keys;
            matchSelector.selectText(match);
            onSelectMatch(match);
        }
    }
    function updateDisplay({keys, letters, pages_by_ref, default_page}) {
        currentPages = pages_by_ref;
        currentDefaultPage = default_page;
        displayTitle.value = keys + ' ' + TR_DELIM + ' ' + letters;
        // Set the current selections to match the translation if possible.
        let strokes = searchModeStrokes.checked;
        let match = strokes ? keys : letters;
        let mapping = strokes ? letters : keys;
        let mappings = lastMatches[match];
        if(mappings) {
            matchSelector.selectText(match);
            mappingSelector.update(mappings);
            mappingSelector.selectText(mapping);
        }
        let startPage = default_page;
        graphFocused = false;
        if(currentLink) {
            for (let page of Object.values(pages_by_ref)) {
                if(currentLink == page.rule_id) {
                    startPage = page;
                    graphFocused = true;
                    break;
                }
            }
        }
        setPage(startPage);
    }
    function updateGUI({search_results, display_data}) {
        if(search_results) {  // New items in the search lists.
            updateSearch(search_results)
        }
        if(display_data) {  // New graphical objects.
            updateDisplay(display_data)
        }
    }

    let cache = new Map();
    function sendRequest({action, args=[], ignoreCache=false}) {
        let boardOpts = JSON.parse(document.querySelector(OPT_SELECTOR + ':checked').value);
        let options = {search_mode_strokes: searchModeStrokes.checked,
                       search_mode_regex: searchModeRegex.checked,
                       board_aspect_ratio: displayBoard.clientWidth / 250,
                       board_show_compound: boardOpts[0],
                       board_show_letters: boardOpts[1],
                       ...queryOptions};
        let requestContent = JSON.stringify({action, args, options});
        let cachedValue = cache.get(requestContent);
        if(cachedValue && !ignoreCache) {
            updateGUI(cachedValue);
        } else {
            $.ajax({
                method: 'POST',
                url: 'request',
                contentType: 'application/json',
                data: requestContent,
                success(value) {
                    cache.set(requestContent, value);
                    updateGUI(value);
                },
                error() {
                    displayDesc.innerHTML = '<span style="color: #D00000;">CONNECTION ERROR</span>';
                }
            });
        }
    }
}

$(document).ready(SpectraClient);
