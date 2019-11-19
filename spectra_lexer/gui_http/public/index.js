const TITLE_DELIM = " -> ";           // Delimiter between keys and letters of translations shown in title bar.
const MORE_TEXT = "(more...)";        // Text displayed as the final match, allowing the user to expand the search.
const SEARCH_EXTEND_INTERVAL = 1000;  // Minimum time in ms between search expansions.
const NODE_SELECTOR = "a.gg";         // CSS selector for graph nodes.

// Add all URL query items as JSON-format options.
var options = {};
let queryParams = new URLSearchParams(window.location.search);
for (let [k, v] of queryParams){
    try{
        options[k] = JSON.parse(v);
    }catch(e){
        console.error(e);
    }
}

$(document).ready(function(){
    class ListHandler {
        constructor(id, onSelectFn) {
            this.active = {};
            this.onSelectFn = onSelectFn;
            this.root = document.getElementById(id);
            this.root.addEventListener("click", this.clickEvent.bind(this));
        }
        selectElem(elem) {
            if(this.root === elem || this.active === elem){
                return false;
            }
            this.active.className = "";
            this.active = elem;
            elem.className = 'selected';
            return true;
        }
        selectText(value) {
            for (let elem of this.root.children){
                if(elem.textContent == value){
                    return this.selectElem(elem);
                }
            }
        }
        clickEvent({target}) {
            if(this.selectElem(target)){
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
            for (let opt of optArray){
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

    const searchInput = document.getElementById("w_input");
    const matchSelector = new ListHandler("w_matches", onSelectMatch);
    const mappingSelector = new ListHandler("w_mappings", onSelectMapping);
    const searchModeStrokes = document.getElementById("w_strokes");
    const searchModeRegex = document.getElementById("w_regex");
    const displayTitle = document.getElementById("w_title");
    const displayText = document.getElementById("w_text");
    const displayDesc = document.getElementById("w_desc");
    const displayBoard = document.getElementById("w_board");
    const displayLink = document.getElementById("w_link");

    var lastMatches = {};
    var lastPageCount = 1;
    function onSelectMatch(text) {
        if(text == MORE_TEXT){
            lastPageCount++;
            doSearch();
        } else {
            let mappings = lastMatches[text];
            mappingSelector.update(mappings);
            onSelectMapping();
        }
    }
    function onSelectMapping(text) {
        let match = matchSelector.value;
        let mappings = text ? [text] : lastMatches[match];
        let translations = [];
        for (let m of mappings) {
            // The order of lexer parameters must be reversed for strokes mode.
            let tr = options.search_mode_strokes ? [match, m] : [m, match];
            translations.push(tr);
        }
        processAction("Query", ...translations);
    }

    function newSearch() {
        lastPageCount = 1;
        doSearch();
    }
    function doSearch() {
        processAction("Search", searchInput.value, lastPageCount);
    }
    searchModeStrokes.addEventListener("change", newSearch);
    searchModeRegex.addEventListener("change", newSearch);
    searchInput.addEventListener("input", newSearch);
    displayTitle.addEventListener("input", function(){
        let params = this.value.split(TITLE_DELIM);
        if(params.length == 2){
            let translation = params.map(s => s.trim());
            processAction("Query", translation);
        }
    });

    var lastLink = "";
    function setPage({graph, intense_graph, caption, board, rule_id}) {
        displayText.innerHTML = graphFocused ? intense_graph : graph;
        displayDesc.textContent = caption;
        displayBoard.innerHTML = board;
        displayLink.style.display = (rule_id ? "" : "none");
        lastLink = rule_id;
    }
    displayLink.addEventListener("click", function(){
        processAction("SearchExamples", lastLink);
        return false;
    });

    var lastAnalysis = null;
    var graphFocused = false;
    function graphAction(ref, clicked) {
        if(lastAnalysis) {
            let page = lastAnalysis.pages_by_ref[ref];
            if(page) {
                graphFocused = clicked;
            } else {
                graphFocused = false;
                page = lastAnalysis.default_page;
            }
            setPage(page);
        }
    }
    $(displayText).on("mouseenter", NODE_SELECTOR, function(){
        if(!graphFocused) {
            let ref = this.href.split("#").pop();
            graphAction(ref, false);
        }
        return false;
    }).on("click", NODE_SELECTOR, function(){
        let ref = this.href.split("#").pop();
        graphAction(ref, true);
        return false;
    }).click(function(){
        graphAction("");
        return false;
    });

    function updateGUI({search_input, search_results, analysis}) {
        if(search_input){  // New example pattern for search textbox.
            searchInput.value = search_input;
        }
        if(search_results) {  // New items in the search lists.
            lastMatches = search_results.matches;
            let keys = Object.keys(lastMatches);
            // If there are unseen results, add a final list item to allow search expansion.
            if(!search_results.is_complete){
                keys.push(MORE_TEXT);
            }
            matchSelector.update(keys);
            // If the new list does not have the previous selection, reset the mappings.
            if(!matchSelector.value){
                mappingSelector.update([]);
            }
            if (keys.length == 1){
                // Automatically select the item if there was only one.
                let [match] = keys;
                matchSelector.selectText(match);
                onSelectMatch(match);
            }
        }
        if(analysis) {  // New graphical objects.
            lastAnalysis = analysis;
            let {keys, letters, pages_by_ref, default_page} = analysis;
            displayTitle.value = keys + TITLE_DELIM + letters;
            // Set the current selections to match the translation if possible.
            let strokes = options.search_mode_strokes;
            let match = strokes ? keys : letters;
            let mapping = strokes ? letters : keys;
            let mappings = lastMatches[match];
            if(mappings) {
                matchSelector.selectText(match)
                mappingSelector.update(mappings);
                mappingSelector.selectText(mapping)
            }
            if(lastLink){
                for(let [ref, page] of Object.entries(pages_by_ref)){
                    if(lastLink==page.rule_id){
                        graphAction(ref, true);
                        return;
                    }
                }
            }
            graphAction();
        }
    }

    function processAction(action, ...args) {
        options.search_mode_strokes = searchModeStrokes.checked;
        options.search_mode_regex = searchModeRegex.checked;
        options.board_aspect_ratio = displayBoard.clientWidth / 250;
        let request = {action, args, options};
        $.ajax({
            method: 'POST',
            url: 'request',
            contentType: 'application/json',
            data: JSON.stringify(request),
            success: updateGUI,
            error() {displayDesc.innerHTML = '<span style="color: #d00000;">CONNECTION ERROR</span>'}
        });
    }

    // Before starting, hide the link.
    displayLink.style.display = "none";
});
