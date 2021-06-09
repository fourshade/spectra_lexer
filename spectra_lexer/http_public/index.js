function SpectraClient() {

    const TR_DELIM = '->';          // Delimiter between keys and letters of translations shown in title bar.
    const MORE_TEXT = '[more...]';  // Text displayed as the final match, allowing the user to expand the search.

    const OPT_SELECTOR = 'input[name="w_boardopts"]';  // CSS selector for board option radio elements.

    class ListHandler {
        constructor(root) {
            this.root = root;
            this.active = {};
        }
        selectElem(elem) {
            if (this.root === elem || this.active === elem) {
                return false;
            }
            this.active.className = "";
            this.active = elem;
            elem.className = 'selected';
            return true;
        }
        selectText(value) {
            for (let elem of this.root.children) {
                if (elem.textContent == value) {
                    return this.selectElem(elem);
                }
            }
        }
        addSelectListener(onSelect) {
            this.root.addEventListener("click", e => {
                if (this.selectElem(e.target)) {
                    onSelect(e.target.textContent);
                }
            });
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
    function elementById(id) {
        return document.getElementById(id);
    }
    const searchInput = elementById("w_input");
    const searchModeStrokes = elementById("w_strokes");
    const searchModeRegex = elementById("w_regex");
    const matchList = new ListHandler(elementById("w_matches"));
    const mappingList = new ListHandler(elementById("w_mappings"));
    const displayTitle = elementById("w_title");
    const displayText = elementById("w_graph");
    const displayDesc = elementById("w_caption");
    const displayBoard = elementById("w_board");
    const displayLink = elementById("w_link");

    let lastMatches = {};
    let lastPageCount = 1;
    function doSearch() {
        let input = searchInput.value;
        sendRequest("search", [input, lastPageCount]);
    }
    function newSearch() {
        lastPageCount = 1;
        doSearch();
    }
    function querySelection(match, mappings) {
        sendRequest("query_match", [match, mappings]);
    }
    function onSelectMatch(match) {
        if (match == MORE_TEXT) {
            lastPageCount++;
            doSearch();
        } else {
            let mappings = lastMatches[match];
            mappingList.update(mappings);
            if (mappings.length) {
                querySelection(match, mappings);
            }
        }
    }
    function onSelectMapping(mapping) {
        if (mapping) {
            let match = matchList.value;
            querySelection(match, [mapping]);
        }
    }
    searchInput.addEventListener("input", newSearch);
    searchModeStrokes.addEventListener("change", newSearch);
    searchModeRegex.addEventListener("change", newSearch);
    matchList.addSelectListener(onSelectMatch);
    mappingList.addSelectListener(onSelectMapping);

    function doQuery() {
        let translation = displayTitle.value.split(TR_DELIM).map(s => s.trim()).filter(s => s);
        if (translation.length == 2) {
            sendRequest("query", translation);
        }
    }
    displayTitle.addEventListener("input", doQuery);
    for (let elem of document.querySelectorAll(OPT_SELECTOR)) {
        elem.addEventListener("click", doQuery);
    }

    let graphFocused = false;
    let currentLink = "";
    function setPage({graph, intense_graph, caption, board, rule_id}) {
        displayText.innerHTML = graphFocused ? intense_graph : graph;
        displayDesc.textContent = caption;
        displayBoard.innerHTML = board;
        displayLink.style.display = (rule_id ? "block" : "none");
        currentLink = rule_id;
    }
    displayLink.addEventListener("click", e => {
        sendRequest("search_examples", [currentLink], true);
        return false;
    });

    let currentPages = {};
    let currentDefaultPage = null;
    let lastNodeRef = null;
    function graphAction(nodeRef, isFocused) {
        let page = currentPages[nodeRef] || currentDefaultPage;
        if (page) {
            lastNodeRef = nodeRef;
            graphFocused = isFocused;
            setPage(page);
        }
    }
    function anchorFragment(elem) {
        return elem.href ? elem.href.split("#").pop() : null;
    }
    displayText.addEventListener("mouseover", e => {
        if (!graphFocused) {
            let nodeRef = anchorFragment(e.target);
            if (nodeRef && nodeRef != lastNodeRef) {
                graphAction(nodeRef, false);
            }
        }
        return false;
    });
    displayText.addEventListener("click", e => {
        let nodeRef = anchorFragment(e.target);
        graphAction(nodeRef, !!nodeRef);
        return false;
    });

    function updateMatches({pattern, results, can_expand}) {
        if (pattern != searchInput.value) {
            searchInput.value = pattern;
        }
        lastMatches = results;
        let keys = Object.keys(results);
        if (can_expand) {
            keys.push(MORE_TEXT);
        }
        matchList.update(keys);
        // If the new list does not have the previous selection, reset the mappings.
        if (!matchList.value) {
            mappingList.update([]);
        }
        if (keys.length == 1) {
            // Automatically select the item if there was only one.
            let [match] = keys;
            matchList.selectText(match);
            onSelectMatch(match);
        }
    }
    function updateSelections({match, mapping}) {
        let mappings = lastMatches[match];
        if (mappings) {
            matchList.selectText(match);
            mappingList.update(mappings);
            mappingList.selectText(mapping);
        }
    }
    function updateDisplay({keys, letters, pages_by_ref, default_page}) {
        let title = keys + ' ' + TR_DELIM + ' ' + letters;
        currentPages = pages_by_ref;
        currentDefaultPage = default_page;
        if (title != displayTitle.value) {
            displayTitle.value = title;
            lastNodeRef = null;
        }
        graphAction(lastNodeRef, false);
    }
    function updateExample(example_ref) {
        graphAction(example_ref, true);
    }
    function updateGUI({matches, selections, display, example_ref}) {
        // Updates must be done *strictly in this order*.
        if (matches) {  // New items in the search lists.
            updateMatches(matches);
        }
        if (selections) {  // New selections in the search lists.
            updateSelections(selections);
        }
        if (display) {  // New graphical objects.
            updateDisplay(display);
        }
        if (example_ref) {  // New example focus page.
            updateExample(example_ref);
        }
    }

    let queryOptions = {};
    let cache = new Map();
    async function sendRequest(action, args, ignoreCache=false) {
        let boardOpts = JSON.parse(document.querySelector(OPT_SELECTOR + ':checked').value);
        let options = {search_mode_strokes: searchModeStrokes.checked,
                       search_mode_regex: searchModeRegex.checked,
                       board_aspect_ratio: displayBoard.clientWidth / 250,
                       board_show_compound: boardOpts[0],
                       board_show_letters: boardOpts[1],
                       ...queryOptions};
        let requestBody = JSON.stringify({action, args, options});
        try {
            let value = cache.get(requestBody);
            if (!value || ignoreCache) {
                let request = {method: 'POST',
                               body: requestBody,
                               headers: {'Content-Type': 'application/json'}};
                let response = await fetch('/request', request);
                value = await response.json();
                cache.set(requestBody, value);
            }
            updateGUI(value);
        } catch(e) {
            displayDesc.innerHTML = '<span style="color: #D00000;">CONNECTION ERROR</span>';
            console.error(e);
        }
    }

    // Parse JSON-based options from the URL query string, then execute startup actions.
    let params = new URLSearchParams(window.location.search);
    for (let [k, v] of params) {
        if (k == 'translation' || k == 'outline') {
            continue;
        }
        try {
            queryOptions[k] = JSON.parse(v);
        } catch(e) {
            console.error(e);
        }
    }
    async function startupSearch(pattern) {
        await sendRequest("search", [pattern, 1]);
        onSelectMatch(pattern);
    }
    if (params.has('translation')) {
        startupSearch(params.get('translation'));
    }
    if (params.has('outline')) {
        searchModeStrokes.checked = true;
        startupSearch(params.get('outline'));
    }
}

window.onload = SpectraClient;
